"""
Silero VAD 模型
"""
import torch
import torchaudio
import numpy as np
import logging
from typing import Optional
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VADModel:
    """
    Silero VAD 模型
    用于检测语音活动
    """
    
    def __init__(self, config: dict):
        """
        初始化 VAD 模型
        
        Args:
            config: 听觉层配置
        """
        self.config = config
        self.threshold = config.get("vad_threshold", 0.5)
        self.min_silence_ms = config.get("vad_min_silence_ms", 500)
        self.model = None
        self.utils = None
    
    async def load_model(self):
        """加载 Silero VAD 模型"""
        logger.info("正在加载 Silero VAD 模型...")
        
        try:
            # 加载 Silero VAD 模型
            model, utils = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
                onnx=False,
                trust_repo=True
            )
            
            self.model = model
            self.utils = utils
            
            logger.info("Silero VAD 模型加载成功")
            
        except Exception as e:
            logger.error(f"加载 Silero VAD 模型失败: {e}")
            raise
    
    async def is_speech(self, audio: np.ndarray) -> bool:
        """
        检测音频是否包含语音
        
        Args:
            audio: 音频数据 (numpy 数组, float32, -1.0 ~ 1.0)
            
        Returns:
            是否包含语音
        """
        if self.model is None:
            raise RuntimeError("VAD 模型未加载")
        
        try:
            # 获取工具函数
            get_speech_timestamps = self.utils[0]
            
            # 转换为 torch tensor
            audio_tensor = torch.from_numpy(audio)
            
            # 获取语音时间戳
            speech_timestamps = get_speech_timestamps(
                audio_tensor,
                self.model,
                threshold=self.threshold,
                sampling_rate=16000
            )
            
            # 如果有语音段，返回 True
            return len(speech_timestamps) > 0
            
        except Exception as e:
            logger.error(f"VAD 检测失败: {e}")
            return False
    
    async def get_speech_segments(self, audio: np.ndarray) -> list:
        """
        获取语音段
        
        Args:
            audio: 音频数据 (numpy 数组)
            
        Returns:
            语音段时间戳列表 [{"start": start_sample, "end": end_sample}, ...]
        """
        if self.model is None:
            raise RuntimeError("VAD 模型未加载")
        
        try:
            # 获取工具函数
            get_speech_timestamps = self.utils[0]
            
            # 转换为 torch tensor
            audio_tensor = torch.from_numpy(audio)
            
            # 获取语音时间戳
            speech_timestamps = get_speech_timestamps(
                audio_tensor,
                self.model,
                threshold=self.threshold,
                sampling_rate=16000
            )
            
            return speech_timestamps
            
        except Exception as e:
            logger.error(f"获取语音段失败: {e}")
            return []


if __name__ == "__main__":
    # 测试 VAD 模型
    import asyncio
    
    async def test_vad():
        # 加载配置
        from utils.config_loader import load_config
        config = load_config()
        auditory_config = config["auditory"]
        
        # 创建 VAD 模型
        vad_model = VADModel(auditory_config)
        await vad_model.load_model()
        
        # 生成测试音频 (1秒静音 + 1秒语音)
        sample_rate = 16000
        duration = 2  # 秒
        
        # 静音部分
        silence = np.zeros(sample_rate, dtype=np.float32)
        
        # 语音部分 (440Hz 正弦波)
        t = np.linspace(0, 1, sample_rate)
        speech = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        
        # 合并
        test_audio = np.concatenate([silence, speech])
        
        # 测试语音检测
        is_speech = await vad_model.is_speech(test_audio)
        print(f"是否包含语音: {is_speech}")
        
        # 获取语音段
        segments = await vad_model.get_speech_segments(test_audio)
        print(f"语音段: {segments}")
    
    asyncio.run(test_vad())
