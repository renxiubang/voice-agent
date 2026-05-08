"""
音频采集和预处理模块
支持两种采集方式：
1. 前端采集（frontend）：通过 WebSocket 接收前端发送的音频流（浏览器已做 AEC）
2. 后端采集（backend）：使用 CoreAudioProcessor 直接从麦克风采集音频（启用系统级 AEC）
"""
import sounddevice as sd
import numpy as np
import logging
from typing import Optional, Callable
import asyncio
from pathlib import Path

# 导入后端采集模块
from .core_audio_processor import CoreAudioProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AudioProcessor:
    """
    音频采集和预处理
    支持前端采集（浏览器 AEC）和后端采集（AVAudioEngine AEC）
    """
    
    def __init__(self):
        self.sample_rate = 16000
        self.channels = 1
        self.dtype = "int16"
        self.blocksize = 1024
        self.stream = None
        self.callback = None
        
        # 输入模式：frontend（前端采集）或 backend（后端采集）
        self.input_mode = "frontend"
        
        # 后端采集处理器
        self.core_audio_processor = None
        
        # 音频缓冲区
        self.audio_buffer = []
        self.buffer_duration_ms = 3000  # 3秒缓冲区
        
    async def init(self, config: dict):
        """
        初始化音频处理器
        
        Args:
            config: 听觉层配置
        """
        self.sample_rate = config.get("sample_rate", 16000)
        self.channels = config.get("channels", 1)
        self.dtype = config.get("dtype", "int16")
        self.input_mode = config.get("input_mode", "frontend")
        
        logger.info(f"音频输入模式: {self.input_mode}")
        
        if self.input_mode == "backend":
            # 后端采集模式：使用 CoreAudioProcessor
            logger.info("初始化后端音频采集（CoreAudioProcessor）...")
            self.core_audio_processor = CoreAudioProcessor(config)
            await self.core_audio_processor.init()
            logger.info("✅ 后端音频采集初始化完成")
            
        else:
            # 前端采集模式：使用 sounddevice（仅用于测试）
            logger.info("前端采集模式：音频将通过 WebSocket 接收")
            
            # 打印可用的音频设备（用于调试）
            logger.info("可用的音频设备:")
            devices = sd.query_devices()
            for i, device in enumerate(devices):
                logger.info(f"  {i}: {device['name']} (输入: {device['max_input_channels']}, 输出: {device['max_output_channels']})")
            
            logger.info("✅ 前端音频采集初始化完成")
        
        logger.info("音频处理器初始化完成")
    
    def set_callback(self, callback: Callable[[bytes], None]):
        """
        设置音频数据回调函数
        
        Args:
            callback: 回调函数，接收音频数据 (bytes)
        """
        self.callback = callback
        
        # 如果是后端采集模式，同时设置 CoreAudioProcessor 的回调
        if self.input_mode == "backend" and self.core_audio_processor:
            self.core_audio_processor.set_callback(callback)
            logger.info("✅ 后端采集回调已设置")
    
    async def start_stream(self):
        """启动音频流（根据 input_mode 选择不同的采集方式）"""
        logger.info(f"正在启动音频流（模式: {self.input_mode}）...")
        
        if self.input_mode == "backend":
            # 后端采集模式：使用 CoreAudioProcessor
            if not self.core_audio_processor:
                raise RuntimeError("CoreAudioProcessor 未初始化")
            
            await self.core_audio_processor.start_stream()
            logger.info("✅ 后端音频流已启动（AVAudioEngine + Voice Processing I/O AEC）")
            
        else:
            # 前端采集模式：音频通过 WebSocket 接收，这里不需要启动本地音频流
            # 但保留 sounddevice 用于本地测试
            logger.info("前端采集模式：音频将通过 WebSocket 接收")
            
            # 可选：启动本地音频流用于测试
            # self._start_local_stream()
            
            logger.info("✅ 前端音频流已启动（WebSocket 接收）")
    
    def _start_local_stream(self):
        """启动本地音频流（用于测试）"""
        def audio_callback(indata, frames, time, status):
            """音频流回调函数"""
            if status:
                logger.warning(f"音频流状态: {status}")
            
            # 转换为 bytes
            audio_bytes = indata.tobytes()
            
            # 调用用户回调
            if self.callback:
                self.callback(audio_bytes)
        
        try:
            # 创建输入流
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                blocksize=self.blocksize,
                callback=audio_callback
            )
            
            # 启动流
            self.stream.start()
            logger.info("本地音频流已启动（测试模式）")
            
        except Exception as e:
            logger.error(f"启动本地音频流失败: {e}")
            raise
    
    async def stop_stream(self):
        """停止音频流（根据 input_mode 选择不同的停止方式）"""
        logger.info(f"正在停止音频流（模式: {self.input_mode}）...")
        
        if self.input_mode == "backend":
            # 后端采集模式：停止 CoreAudioProcessor
            if self.core_audio_processor:
                await self.core_audio_processor.stop_stream()
                logger.info("✅ 后端音频流已停止")
            
        else:
            # 前端采集模式：停止本地音频流（如果有）
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None
                logger.info("本地音频流已停止")
            
            # 清空前端音频队列
            while not self.frontend_audio_queue.empty():
                try:
                    self.frontend_audio_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            
            logger.info("✅ 前端音频流已停止（WebSocket 接收已关闭）")
    
    async def record_audio(self, duration_ms: int) -> bytes:
        """
        录制音频（根据 input_mode 选择不同的录制方式）
        
        Args:
            duration_ms: 录制时长 (毫秒)
            
        Returns:
            音频数据 (bytes, PCM 16-bit)
        """
        logger.info(f"正在录制音频 ({duration_ms} ms)...")
        
        if self.input_mode == "backend" and self.core_audio_processor:
            # 后端采集模式：使用 CoreAudioProcessor
            logger.info("使用后端采集模式录制音频...")
            
            # TODO: 实现 CoreAudioProcessor 的录制功能
            # 暂时使用占位符
            audio_bytes = b'\x00' * int(self.sample_rate * duration_ms / 1000 * 2)  # 16-bit = 2 bytes/sample
            
        else:
            # 前端采集模式：使用 sounddevice 录制（用于测试）
            logger.info("使用本地音频流录制音频...")
            
            # 计算采样点数
            num_samples = int(self.sample_rate * duration_ms / 1000)
            
            # 录制音频
            audio_data = sd.rec(
                num_samples,
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype
            )
            
            # 等待录制完成
            sd.wait()
            
            # 转换为 bytes
            audio_bytes = audio_data.tobytes()
        
        logger.info(f"音频录制完成: {len(audio_bytes)} bytes")
        return audio_bytes
    
    def process_audio(self, audio_bytes: bytes) -> np.ndarray:
        """
        预处理音频数据
        
        Args:
            audio_bytes: 音频数据 (bytes, PCM 16-bit)
            
        Returns:
            预处理后的音频数据 (numpy 数组, float32, -1.0 ~ 1.0)
        """
        # 转换为 numpy 数组
        audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        
        return audio_float32
    
    async def enable_echo_cancellation(self):
        """
        启用回声消除（根据 input_mode 选择不同的实现）
        """
        if self.input_mode == "backend":
            # 后端采集模式：使用 AVAudioEngine 的 Voice Processing I/O
            logger.info("✅ 后端采集模式：AVAudioEngine 已自动启用 Voice Processing I/O AEC")
            logger.info("无需额外配置，AVAudioEngine 会在启动时自动启用系统级 AEC")
            
        else:
            # 前端采集模式：使用浏览器 AEC
            logger.info("✅ 前端采集模式：请在浏览器中启用 echoCancellation")
            logger.info("示例代码：")
            logger.info("""
                const stream = await navigator.mediaDevices.getUserMedia({
                    audio: {
                        echoCancellation: true,  // 启用浏览器回声消除
                        noiseSuppression: true,
                        autoGainControl: true
                    }
                });
            """)


async def main():
    """测试音频采集"""
    # 初始化音频处理器
    processor = AudioProcessor()
    config = {
        "sample_rate": 16000,
        "channels": 1,
        "dtype": "int16"
    }
    await processor.init(config)
    
    # 录制 3 秒音频
    audio_bytes = await processor.record_audio(3000)
    print(f"录制音频长度: {len(audio_bytes)} bytes")
    
    # 预处理音频
    audio_float32 = processor.process_audio(audio_bytes)
    print(f"预处理后音频长度: {len(audio_float32)} samples")
    print(f"音频范围: [{np.min(audio_float32):.3f}, {np.max(audio_float32):.3f}]")


if __name__ == "__main__":
    asyncio.run(main())
