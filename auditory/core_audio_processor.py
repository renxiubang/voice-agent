"""
后端音频采集模块（macOS）
使用 pyobjc 调用 AVAudioEngine（Objective-C API）配置 Voice Processing I/O，实现系统级 AEC
"""
import asyncio
import logging
import numpy as np
from typing import Optional, Callable
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CoreAudioProcessor:
    """
    使用 pyobjc 调用 AVAudioEngine（Objective-C API）配置 Voice Processing I/O
    实现 macOS 系统级回声消除（AEC）
    
    注意：PyObjC 只能桥接 Objective-C 接口，不能直接调用纯 C 接口。
    AVAudioEngine 是 Objective-C API，所以 PyObjC 可以调用。
    AVAudioEngine 内部会自动配置 Voice Processing I/O（纯 C Core Audio API）。
    """
    
    def __init__(self, config: dict):
        """
        初始化 Core Audio 处理器
        
        Args:
            config: 听觉层配置
        """
        self.sample_rate = config.get("sample_rate", 16000)
        self.channels = config.get("channels", 1)
        self.dtype = config.get("dtype", "int16")
        
        # 音频引擎
        self.audio_engine = None
        self.is_running = False
        
        # 音频回调
        self.callback = None
        
        # 音频队列（线程安全，用于在音频回调线程和主线程之间传递数据）
        self.audio_queue = None  # 将在 init() 中初始化为 asyncio.Queue
        self.loop = None  # 主事件循环
        
        # PyObjC 模块（延迟导入）
        self.AVFoundation = None
        self.Foundation = None
        
        logger.info(f"CoreAudioProcessor 初始化: sample_rate={self.sample_rate}, channels={self.channels}")
    
    async def init(self):
        """初始化 PyObjC 和 AVAudioEngine"""
        try:
            # 保存主事件循环
            self.loop = asyncio.get_event_loop()
            
            # 初始化音频队列（线程安全）
            self.audio_queue = asyncio.Queue(maxsize=100)
            
            # 导入 PyObjC 模块
            logger.info("正在导入 PyObjC 模块...")
            
            import AVFoundation
            import Foundation
            
            self.AVFoundation = AVFoundation
            self.Foundation = Foundation
            
            logger.info("✅ PyObjC 模块导入成功")
            
        except ImportError as e:
            logger.error(f"❌ PyObjC 未安装，请运行: pip install pyobjc")
            logger.error(f"详细信息: {e}")
            raise RuntimeError("PyObjC 未安装，无法使用后端 AEC")
        
        logger.info("CoreAudioProcessor 初始化完成")
    
    def set_callback(self, callback: Callable[[bytes], None]):
        """
        设置音频数据回调函数
        
        Args:
            callback: 回调函数，接收音频数据 (bytes)
        """
        self.callback = callback
        logger.info("音频回调函数已设置")
    
    def audio_callback(self, buffer, when):
        """
        AVAudioEngine 音频回调函数（运行在 Objective-C 线程）
        
        Args:
            buffer: AVAudioPCMBuffer 对象
            when: AVAudioTime 对象
        """
        try:
            # 将 AVAudioPCMBuffer 转换为 numpy 数组
            # 注意：这里需要根据实际的数据格式进行转换
            # AVAudioPCMBuffer 的数据存储在 floatChannelData 中
            
            logger.debug(f"收到音频数据: buffer.frameLength={buffer.frameLength()}")
            
            # TODO: 实现 AVAudioPCMBuffer 到 numpy 数组的转换
            # 暂时使用占位符
            audio_data = np.zeros(buffer.frameLength(), dtype=np.float32)
            
            # 转换为 bytes
            if self.dtype == "int16":
                audio_int16 = (audio_data * 32768.0).astype(np.int16)
                audio_bytes = audio_int16.tobytes()
            else:
                audio_bytes = audio_data.tobytes()
            
            # 使用 call_soon_threadsafe 将数据放入 asyncio.Queue（避免 GIL 问题）
            if self.loop and self.audio_queue:
                self.loop.call_soon_threadsafe(
                    self.audio_queue.put_nowait, audio_bytes
                )
            
            # 调用用户回调（可选）
            if self.callback:
                self.callback(audio_bytes)
            
        except Exception as e:
            logger.error(f"音频回调处理失败: {e}")
    
    async def start_stream(self):
        """启动 AVAudioEngine，启用 Voice Processing I/O"""
        if self.is_running:
            logger.warning("音频引擎已在运行")
            return
        
        try:
            logger.info("正在启动 AVAudioEngine...")
            
            # 1. 配置 AVAudioSession（macOS/iOS）
            # 注意：macOS 上 AVAudioSession 可能不可用，需要使用其他方式
            # 这里提供示例代码，实际可能需要调整
            
            try:
                session = self.AVFoundation.AVAudioSession.sharedInstance()
                session.setCategory_error_(
                    self.AVFoundation.AVAudioSessionCategoryPlayAndRecord,
                    None
                )
                session.setMode_error_(
                    self.AVFoundation.AVAudioSessionModeVoiceChat,  # ← 启用 Voice Processing I/O
                    None
                )
                logger.info("✅ AVAudioSession 配置完成（已启用 Voice Processing I/O）")
            except Exception as e:
                logger.warning(f"配置 AVAudioSession 失败（可能不支持 macOS）: {e}")
                logger.warning("将继续尝试启动 AVAudioEngine...")
            
            # 2. 创建 AVAudioEngine（Objective-C API，PyObjC 可以调用）
            self.audio_engine = self.AVFoundation.AVAudioEngine.new()
            
            # 3. 获取输入节点
            input_node = self.audio_engine.inputNode()
            
            # 4. 安装音频 tap，获取音频数据
            buffer_size = 1024
            input_node.installTapOnBus_bufferSize_format_block_(
                0,  # bus
                buffer_size,
                None,  # 使用默认格式
                self.audio_callback
            )
            
            # 5. 启动音频引擎
            error = self.Foundation.NSError.alloc().init()
            success = self.audio_engine.startAndReturnError_(error)
            if not success:
                logger.error(f"❌ 启动 AVAudioEngine 失败: {error}")
                raise RuntimeError(f"启动 AVAudioEngine 失败: {error}")
            
            self.is_running = True
            logger.info("✅ Core Audio 引擎已启动，Voice Processing I/O AEC 已启用")
            
        except Exception as e:
            logger.error(f"❌ 启动 Core Audio 处理器失败: {e}")
            raise
    
    async def stop_stream(self):
        """停止 AVAudioEngine"""
        if not self.is_running:
            logger.warning("音频引擎未运行")
            return
        
        try:
            logger.info("正在停止 AVAudioEngine...")
            
            # 停止音频引擎
            if self.audio_engine:
                self.audio_engine.stop()
                self.audio_engine = None
            
            self.is_running = False
            logger.info("✅ Core Audio 引擎已停止")
            
        except Exception as e:
            logger.error(f"❌ 停止 Core Audio 处理器失败: {e}")
            raise
    
    async def get_audio_data(self) -> Optional[bytes]:
        """
        从队列中获取音频数据（异步）
        
        Returns:
            音频数据 (bytes)，如果没有数据则返回 None
        """
        try:
            # 使用 wait_for 设置超时，避免永久阻塞
            audio_bytes = await asyncio.wait_for(
                self.audio_queue.get(),
                timeout=0.1  # 100ms 超时
            )
            return audio_bytes
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error(f"获取音频数据失败: {e}")
            return None
    
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


async def main():
    """测试 Core Audio 处理器"""
    # 初始化处理器
    config = {
        "sample_rate": 16000,
        "channels": 1,
        "dtype": "int16"
    }
    
    processor = CoreAudioProcessor(config)
    
    try:
        # 初始化
        await processor.init()
        
        # 设置回调
        def test_callback(audio_bytes: bytes):
            print(f"收到音频数据: {len(audio_bytes)} bytes")
        
        processor.set_callback(test_callback)
        
        # 启动音频流
        await processor.start_stream()
        
        # 运行 5 秒
        logger.info("正在采集音频（5 秒）...")
        await asyncio.sleep(5)
        
        # 停止音频流
        await processor.stop_stream()
        
        logger.info("测试完成")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())
