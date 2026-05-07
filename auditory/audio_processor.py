"""
音频采集和预处理模块
"""
import sounddevice as sd
import numpy as np
import logging
from typing import Optional, Callable
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AudioProcessor:
    """
    音频采集和预处理
    使用 sounddevice 采集麦克风音频，支持回声消除
    """
    
    def __init__(self):
        self.sample_rate = 16000
        self.channels = 1
        self.dtype = "int16"
        self.blocksize = 1024
        self.stream = None
        self.callback = None
        
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
        
        # 打印可用的音频设备
        logger.info("可用的音频设备:")
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            logger.info(f"  {i}: {device['name']} (输入: {device['max_input_channels']}, 输出: {device['max_output_channels']})")
        
        # 设置默认输入设备 (macOS 通常使用 "Built-in Microphone")
        try:
            sd.default.device = sd.query_devices(kind="input")["name"]
            logger.info(f"默认输入设备: {sd.default.device}")
        except Exception as e:
            logger.warning(f"设置默认输入设备失败: {e}")
        
        logger.info("音频处理器初始化完成")
    
    def set_callback(self, callback: Callable[[bytes], None]):
        """
        设置音频数据回调函数
        
        Args:
            callback: 回调函数，接收音频数据 (bytes)
        """
        self.callback = callback
    
    async def start_stream(self):
        """启动音频流"""
        logger.info("正在启动音频流...")
        
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
            logger.info("音频流已启动")
            
        except Exception as e:
            logger.error(f"启动音频流失败: {e}")
            raise
    
    async def stop_stream(self):
        """停止音频流"""
        logger.info("正在停止音频流...")
        
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            
        logger.info("音频流已停止")
    
    async def record_audio(self, duration_ms: int) -> bytes:
        """
        录制音频
        
        Args:
            duration_ms: 录制时长 (毫秒)
            
        Returns:
            音频数据 (bytes, PCM 16-bit)
        """
        logger.info(f"正在录制音频 ({duration_ms} ms)...")
        
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
        启用回声消除 (macOS Voice Processing I/O)
        注意：这需要 Core Audio API 支持，sounddevice 可能不直接支持
        """
        logger.warning("macOS 回声消除需要通过 Core Audio API 实现")
        logger.warning("sounddevice 可能不直接支持回声消除")
        logger.warning("建议使用其他音频库 (如 pyaudio) 或系统级回声消除")
        
        # TODO: 实现 macOS Voice Processing I/O 回声消除
        # 可能需要使用 pyaudio 或直接调用 Core Audio API


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
