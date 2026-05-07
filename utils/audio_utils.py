"""
音频处理工具
"""
import numpy as np
from typing import Tuple


def bytes_to_numpy(audio_bytes: bytes, sample_rate: int = 16000) -> np.ndarray:
    """
    将字节流转换为 numpy 数组
    
    Args:
        audio_bytes: 音频字节流 (PCM 16-bit)
        sample_rate: 采样率
        
    Returns:
        numpy 数组 (float32, -1.0 ~ 1.0)
    """
    # 将字节流转换为 int16 数组
    audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
    
    # 转换为 float32 (-1.0 ~ 1.0)
    audio_float32 = audio_int16.astype(np.float32) / 32768.0
    
    return audio_float32


def numpy_to_bytes(audio_array: np.ndarray) -> bytes:
    """
    将 numpy 数组转换为字节流
    
    Args:
        audio_array: numpy 数组 (float32, -1.0 ~ 1.0)
        
    Returns:
        音频字节流 (PCM 16-bit)
    """
    # 限制范围在 -1.0 ~ 1.0
    audio_clipped = np.clip(audio_array, -1.0, 1.0)
    
    # 转换为 int16
    audio_int16 = (audio_clipped * 32768.0).astype(np.int16)
    
    # 转换为字节流
    audio_bytes = audio_int16.tobytes()
    
    return audio_bytes


def resample_audio(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """
    重采样音频
    
    Args:
        audio: 音频数据 (numpy 数组)
        orig_sr: 原始采样率
        target_sr: 目标采样率
        
    Returns:
        重采样后的音频数据
    """
    from scipy import signal
    
    # 计算重采样比例
    num = int(len(audio) * target_sr / orig_sr)
    
    # 重采样
    resampled = signal.resample(audio, num)
    
    return resampled.astype(np.float32)


def normalize_audio(audio: np.ndarray) -> np.ndarray:
    """
    归一化音频
    
    Args:
        audio: 音频数据 (numpy 数组)
        
    Returns:
        归一化后的音频数据
    """
    # 计算最大绝对值
    max_val = np.max(np.abs(audio))
    
    # 如果最大绝对值为 0，返回原音频
    if max_val == 0:
        return audio
    
    # 归一化
    normalized = audio / max_val
    
    return normalized.astype(np.float32)


def split_audio_by_vad(audio: np.ndarray, sample_rate: int, 
                       vad_model, threshold: float = 0.5) -> list:
    """
    根据 VAD 检测结果分割音频
    
    Args:
        audio: 音频数据 (numpy 数组)
        sample_rate: 采样率
        vad_model: VAD 模型
        threshold: VAD 阈值
        
    Returns:
        分割后的音频片段列表
    """
    # 使用 VAD 模型检测语音活动
    speech_timestamps = vad_model.get_speech_timestamps(audio, threshold=threshold)
    
    # 分割音频
    segments = []
    for ts in speech_timestamps:
        start_sample = int(ts["start"] * sample_rate)
        end_sample = int(ts["end"] * sample_rate)
        segment = audio[start_sample:end_sample]
        segments.append(segment)
    
    return segments


if __name__ == "__main__":
    # 测试音频工具
    import numpy as np
    
    # 生成测试音频 (1秒，440Hz 正弦波)
    sample_rate = 16000
    t = np.linspace(0, 1, sample_rate)
    test_audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    
    # 测试 numpy_to_bytes 和 bytes_to_numpy
    audio_bytes = numpy_to_bytes(test_audio)
    print(f"音频字节流长度: {len(audio_bytes)} bytes")
    
    audio_recovered = bytes_to_numpy(audio_bytes, sample_rate)
    print(f"恢复后的音频长度: {len(audio_recovered)} samples")
    
    # 测试归一化
    normalized = normalize_audio(test_audio)
    print(f"归一化前最大值: {np.max(np.abs(test_audio))}")
    print(f"归一化后最大值: {np.max(np.abs(normalized))}")
