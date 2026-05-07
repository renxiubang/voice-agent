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
    
    async def initialize_modules(self):
        """初始化所有模块"""
        logger.info("正在初始化模块...")
        
        # 初始化听觉层
        from auditory import audio_processor, vad, speaker_recognition, asr
        
        self.audio_processor = audio_processor
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
        
        # 初始化发声层
        from tts import piper_tts
        
        self.tts_engine = piper_tts.PiperTTSModel(self.config["tts"])
        await self.tts_engine.load_model()
        
        logger.info("所有模块初始化完成")
    
    async def auditory_loop(self):
        """
        听觉层主循环
        从 audio_queue 取出音频，进行 VAD + 声纹识别 + ASR
        """
        logger.info("听觉层循环启动")
        
        while self.running:
            try:
                # 从 audio_queue 取出音频
                audio_data = await self.audio_queue.get()
                
                # 转换为 numpy 数组
                import numpy as np
                audio_float32 = np.frombuffer(audio_data, dtype=np.int16).astype(
                    np.float32
                ) / 32768.0
                
                # VAD 检测
                is_speech = await self.vad_model.is_speech(audio_float32)
                
                if is_speech:
                    # 声纹识别
                    speaker_id = await self.speaker_model.recognize(audio_float32)
                    
                    # 如果是目标说话人，进行 ASR
                    if speaker_id == "target_speaker":
                        text = await self.asr_model.transcribe(audio_float32)
                        
                        # 放入 text_queue
                        await self.text_queue.put(text)
                        logger.info(f"识别文本: {text}")
                
            except Exception as e:
                logger.error(f"听觉层错误: {e}")
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
        发声层主循环
        从 llm_queue 取出文本，拼接后送入 TTS
        """
        logger.info("发声层循环启动")
        
        buffer = ""
        tts_config = self.config["tts"]
        buffer_size = tts_config.get("buffer_size", 20)
        
        while self.running:
            try:
                # 从 llm_queue 取出 token
                token = await self.llm_queue.get()
                buffer += token
                
                # 遇到标点符号或缓冲区满，送入 TTS
                if token in "，。！？；" or len(buffer) >= buffer_size:
                    # TTS 生成音频
                    audio_data = await self.tts_engine.synthesize(buffer)
                    buffer = ""
                    
                    # 放入 tts_queue
                    await self.tts_queue.put(audio_data)
                
            except Exception as e:
                logger.error(f"发声层错误: {e}")
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
