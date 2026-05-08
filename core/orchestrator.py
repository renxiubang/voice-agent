"""
异步编排器 - 串联四个模块
"""
import asyncio
import logging
from typing import Optional
from core.queues import (
    get_audio_queue,
    get_text_queue,
    get_llm_queue,
    get_tts_queue,
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Orchestrator:
    """
    异步编排器
    负责启动和管理各个模块，串联全链路流式处理
    """
    
    def __init__(self, config: dict):
        """
        初始化编排器
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.tasks = []
        self.running = False
        
        # 获取队列
        self.audio_queue = get_audio_queue()
        self.text_queue = get_text_queue()
        self.llm_queue = get_llm_queue()
        self.tts_queue = get_tts_queue()
        
        # 模块实例（延迟初始化）
        self.audio_processor = None
        self.vad_model = None
        self.speaker_model = None
        self.asr_model = None
        self.llm_model = None
        self.tts_engine = None
        
        # 双讲检测：TTS 播放状态
        self.tts_playing = False
        self.tts_playing_lock = asyncio.Lock()
        
        # 打断机制：打断事件
        self.barge_in_event = asyncio.Event()
        
        logger.info("异步编排器初始化完成（支持双讲检测 + 打断机制）")
    
    async def initialize_modules(self):
        """初始化所有模块"""
        logger.info("正在初始化模块...")
        
        # 初始化听觉层
        from auditory.audio_processor import AudioProcessor
        from auditory import vad, speaker_recognition, asr

        self.audio_processor = AudioProcessor()
        await self.audio_processor.init(self.config["auditory"])
        
        self.vad_model = vad.VADModel(self.config["auditory"])
        await self.vad_model.load_model()
        
        self.speaker_model = speaker_recognition.SpeakerRecognitionModel(
            self.config["auditory"]
        )
        await self.speaker_model.load_model()
        
        self.asr_model = asr.ASRModel(self.config["auditory"])
        await self.asr_model.load_model()
        
        # 初始化认知层
        from cognition import llm
        
        self.llm_model = llm.LLMModel(self.config["cognition"])
        await self.llm_model.load_model()
        
        # 初始化发声层 (MLX-Audio + Kokoro)
        from tts import mlx_tts
        
        self.tts_engine = mlx_tts.MLXTTSModel(self.config["tts"])
        await self.tts_engine.load_model()
        
        logger.info("所有模块初始化完成")
    
    async def auditory_loop(self):
        """
        听觉层主循环
        从 audio_queue 取出音频，进行 VAD + 声纹识别 + ASR
        支持双讲检测：TTS 播放时暂停声纹比对和 ASR
        支持打断机制：检测到用户语音时触发打断
        """
        logger.info("🎧 听觉层循环启动（支持双讲检测 + 打断机制）")
        audio_chunk_count = 0
        
        while self.running:
            try:
                # 双讲检测：检查 TTS 是否正在播放
                async with self.tts_playing_lock:
                    tts_playing = self.tts_playing
                
                # 从 audio_queue 取出音频
                audio_data = await self.audio_queue.get()
                audio_chunk_count += 1
                
                # 记录收到的音频数据
                logger.info(f"📥 听觉层收到音频块 #{audio_chunk_count}: {len(audio_data)} 字节 (TTS播放中: {tts_playing})")
                
                # 转换为 numpy 数组
                import numpy as np
                audio_float32 = np.frombuffer(audio_data, dtype=np.int16).astype(
                    np.float32
                ) / 32768.0
                
                logger.debug(f"音频转换完成: {len(audio_float32)} 样本, 范围: [{np.min(audio_float32):.3f}, {np.max(audio_float32):.3f}]")
                
                # VAD 检测
                is_speech = await self.vad_model.is_speech(audio_float32)
                logger.debug(f"VAD 检测结果: is_speech={is_speech}")
                
                if is_speech:
                    logger.info(f"🗣️  检测到语音活动 (块 #{audio_chunk_count})")
                    
                    # 打断机制：如果 TTS 正在播放，触发打断
                    if tts_playing:
                        logger.info("🚨 检测到用户语音，触发打断！")
                        self.barge_in_event.set()  # 触发打断事件
                        
                        # 清空 TTS 队列
                        tts_queue_size_before = self.tts_queue.qsize()
                        while not self.tts_queue.empty():
                            try:
                                self.tts_queue.get_nowait()
                            except asyncio.QueueEmpty:
                                break
                        
                        logger.info(f"✅ 打断完成：TTS 队列已清空 ({tts_queue_size_before} -> 0)")
                    
                    # 声纹识别
                    logger.debug("开始声纹识别...")
                    speaker_id = await self.speaker_model.recognize(audio_float32)
                    logger.info(f"声纹识别结果: {speaker_id}")
                    
                    # 如果是目标说话人，进行 ASR
                    if speaker_id == "target_speaker":
                        logger.info("✅ 目标说话人确认，开始 ASR 识别...")
                        text = await self.asr_model.transcribe(audio_float32)
                        
                        if text:
                            # 放入 text_queue
                            await self.text_queue.put(text)
                            logger.info(f"📝 ASR 识别文本: {text}")
                            logger.debug(f"文本已放入队列 (队列大小: {self.text_queue.qsize()})")
                        else:
                            logger.warning("⚠️  ASR 未识别到文本")
                    else:
                        logger.info(f"❌ 非目标说话人: {speaker_id}")
                else:
                    logger.debug(f"未检测到语音活动 (块 #{audio_chunk_count})")
                
            except Exception as e:
                logger.error(f"❌ 听觉层错误: {e}")
                import traceback
                logger.error(traceback.format_exc())
                await asyncio.sleep(0.1)
    
    async def cognition_loop(self):
        """
        认知层主循环
        从 text_queue 取出文本，调用 LLM 生成回复（流式）
        """
        logger.info("认知层循环启动")
        
        while self.running:
            try:
                # 从 text_queue 取出文本
                text = await self.text_queue.get()
                
                # LLM 流式推理
                async for token in self.llm_model.generate_stream(text):
                    # 逐 token 放入 llm_queue
                    await self.llm_queue.put(token)
                
            except Exception as e:
                logger.error(f"认知层错误: {e}")
                await asyncio.sleep(0.1)
    
    async def tts_loop(self):
        """
        发声层主循环（真正流式输出）
        从 llm_queue 取出文本，使用流式 TTS 逐块输出音频
        支持打断机制：监听 barge_in_event
        """
        logger.info("发声层循环启动（流式输出，支持打断机制）")
        
        buffer = ""
        tts_config = self.config["tts"]
        buffer_size = tts_config.get("buffer_size", 20)
        
        while self.running:
            try:
                # 检查是否需要打断
                if self.barge_in_event.is_set():
                    logger.info("🚨 收到打断信号，停止 TTS 合成")
                    
                    # 清空缓冲区
                    buffer = ""
                    
                    # 清空 LLM 队列（停止接收新的 token）
                    while not self.llm_queue.empty():
                        try:
                            self.llm_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                    
                    # 重置打断事件
                    self.barge_in_event.clear()
                    
                    # 继续循环，等待新的输入
                    continue
                
                # 从 llm_queue 取出 token
                token = await self.llm_queue.get()
                buffer += token
                
                # 遇到标点符号或缓冲区满，送入 TTS（流式）
                if token in "，。！？；" or len(buffer) >= buffer_size:
                    logger.debug(f"TTS 流式合成: {buffer}")
                    
                    # 设置 TTS 播放状态为 True（双讲检测）
                    async with self.tts_playing_lock:
                        self.tts_playing = True
                    
                    # 使用流式 TTS，逐块输出音频
                    chunk_count = 0
                    async for audio_chunk in self.tts_engine.synthesize_stream(buffer):
                        # 检查是否需要打断（在合成过程中）
                        if self.barge_in_event.is_set():
                            logger.info("🚨 合成过程中收到打断信号，停止合成")
                            break
                        
                        # 立即将每个音频块放入 tts_queue
                        await self.tts_queue.put(audio_chunk)
                        chunk_count += 1
                    
                    logger.debug(f"TTS 流式合成完成: {chunk_count} 块")
                    buffer = ""
                    
                    # 设置 TTS 播放状态为 False（双讲检测）
                    async with self.tts_playing_lock:
                        self.tts_playing = False
                
            except Exception as e:
                logger.error(f"发声层错误: {e}")
                # 发生错误时，确保 TTS 播放状态被重置
                async with self.tts_playing_lock:
                    self.tts_playing = False
                await asyncio.sleep(0.1)
    
    async def start(self):
        """启动所有模块"""
        # 初始化模块
        await self.initialize_modules()
        
        # 启动主循环
        self.running = True
        
        logger.info("启动异步编排器...")
        self.tasks = [
            asyncio.create_task(self.auditory_loop()),
            asyncio.create_task(self.cognition_loop()),
            asyncio.create_task(self.tts_loop()),
        ]
        
        # 等待所有任务完成
        await asyncio.gather(*self.tasks)
    
    async def stop(self):
        """停止所有模块"""
        logger.info("停止异步编排器...")
        self.running = False
        
        # 取消所有任务
        for task in self.tasks:
            task.cancel()
        
        # 等待任务取消
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        logger.info("所有模块已停止")


async def main():
    """测试入口"""
    from utils.config_loader import load_config
    
    # 加载配置
    config = load_config()
    
    # 创建编排器
    orchestrator = Orchestrator(config)
    
    try:
        # 启动编排器
        await orchestrator.start()
    except KeyboardInterrupt:
        # 停止编排器
        await orchestrator.stop()


if __name__ == "__main__":
    asyncio.run(main())
