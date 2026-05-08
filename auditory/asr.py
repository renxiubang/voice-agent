"""
Whisper ASR 模型 (使用 pywhispercpp)
"""
import numpy as np
import logging
from typing import Optional
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ASRModel:
    """
    Whisper ASR 模型
    使用 pywhispercpp (Whisper C++ 实现)
    """
    
    def __init__(self, config: dict):
        """
        初始化 ASR 模型
        
        Args:
            config: 听觉层配置
        """
        self.config = config
        self.model_name = config.get("asr_model", "medium")
        self.language = config.get("asr_language", "zh")
        self.model_path = config.get("asr_model_path")  # 本地模型路径（可选）
        self.model = None
    
    async def load_model(self):
        """加载 Whisper 模型"""
        logger.info(f"正在加载 Whisper 模型: {self.model_name}")
        
        try:
            # 导入 pywhispercpp
            from pywhispercpp.model import Model
            
            # 优先使用配置的本地模型路径
            if self.model_path and Path(self.model_path).exists():
                model_arg = str(Path(self.model_path).absolute())
                logger.info(f"使用配置的本地模型路径: {self.model_path}")
            else:
                # 直接使用模型名称（pywhispercpp 会自动下载官方模型）
                model_arg = self.model_name
                logger.info(f"使用 pywhispercpp 官方模型: {self.model_name}")
            
            # 加载模型
            self.model = Model(
                model=model_arg,
                n_threads=4  # 使用 4 个线程
            )
            
            logger.info(f"Whisper 模型加载成功")
            
        except Exception as e:
            logger.error(f"加载 Whisper 模型失败: {e}")
            raise
    
    async def transcribe(self, audio: np.ndarray) -> str:
        """
        语音识别
        
        Args:
            audio: 音频数据 (numpy 数组, float32, -1.0 ~ 1.0)
            
        Returns:
            识别文本
        """
        if self.model is None:
            raise RuntimeError("ASR 模型未加载")
        
        try:
            # 使用 pywhispercpp 进行语音识别
            segments = self.model.transcribe(
                audio,
                language=self.language
            )
            
            # 提取文本
            text = " ".join([segment.text for segment in segments])
            
            logger.info(f"ASR 识别结果: {text}")
            return text.strip()
            
        except Exception as e:
            logger.error(f"语音识别失败: {e}")
            return ""
    
    async def transcribe_file(self, file_path: str) -> str:
        """
        识别音频文件
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            识别文本
        """
        if self.model is None:
            raise RuntimeError("ASR 模型未加载")
        
        try:
            # 使用 pywhispercpp 识别音频文件
            segments = self.model.transcribe(
                file_path,
                language=self.language
            )
            
            # 提取文本
            text = " ".join([segment.text for segment in segments])
            
            logger.info(f"ASR 文件识别结果: {text}")
            return text.strip()
            
        except Exception as e:
            logger.error(f"音频文件识别失败: {e}")
            return ""


if __name__ == "__main__":
    # 测试 ASR 模型
    import asyncio
    import soundfile as sf
    
    async def test_asr():
        # 加载配置
        from utils.config_loader import load_config
        config = load_config()
        auditory_config = config["auditory"]
        
        # 创建 ASR 模型
        asr_model = ASRModel(auditory_config)
        await asr_model.load_model()
        
        # 测试音频文件
        test_file = "test_audio.wav"  # 需要准备测试音频文件
        
        if Path(test_file).exists():
            text = await asr_model.transcribe_file(test_file)
            print(f"识别结果: {text}")
        else:
            print(f"测试音频文件 {test_file} 不存在")
            
            # 生成测试音频 (1秒，440Hz 正弦波)
            sample_rate = 16000
            t = np.linspace(0, 1, sample_rate)
            test_audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)
            
            # 保存为 WAV 文件
            sf.write(test_file, test_audio, sample_rate)
            print(f"已生成测试音频文件: {test_file}")
            
            # 识别测试音频
            text = await asr_model.transcribe(test_audio)
            print(f"识别结果: {text}")
    
    asyncio.run(test_asr())
