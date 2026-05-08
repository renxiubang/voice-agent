#!/usr/bin/env python3
"""
声纹注册脚本
用于录制用户语音并注册到声纹数据库
"""
import asyncio
import numpy as np
import sounddevice as sd
import soundfile as sf
from pathlib import Path
import os

# 设置 HuggingFace 镜像
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from auditory.speaker_recognition import SpeakerRecognitionModel
from utils.config_loader import load_config


async def record_audio(duration: float = 5.0, sample_rate: int = 16000) -> np.ndarray:
    """
    录制音频
    
    Args:
        duration: 录制时长（秒）
        sample_rate: 采样率
        
    Returns:
        音频数据 (numpy 数组, float32)
    """
    print(f"\n🎤 准备录制...")
    print(f"请说一些话，比如：'你好，我是XXX，这是我的声纹注册样本。'")
    print(f"录制时长：{duration} 秒")
    print(f"3秒后开始录制...")
    
    await asyncio.sleep(3)
    
    print(f"🔴 开始录制！")
    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype='float32'
    )
    sd.wait()
    print(f"⚫ 录制完成！")
    
    # 转换为一维数组
    audio = audio.squeeze()
    
    return audio


async def main():
    # 加载配置
    print("=" * 50)
    print("声纹注册工具")
    print("=" * 50)
    
    config = load_config()
    auditory_config = config["auditory"]
    
    # 创建声纹识别模型
    print("\n📦 正在加载声纹识别模型...")
    model = SpeakerRecognitionModel(auditory_config)
    await model.load_model()
    print("✅ 模型加载成功！")
    
    # 获取说话人 ID
    print("\n" + "=" * 50)
    speaker_id = input("请输入说话人 ID (默认: target_speaker): ").strip()
    if not speaker_id:
        speaker_id = "target_speaker"
    
    # 录制多个样本
    print("\n" + "=" * 50)
    print(f"正在为说话人 [{speaker_id}] 注册声纹")
    print("=" * 50)
    
    num_samples = 3
    audio_samples = []
    
    for i in range(num_samples):
        print(f"\n📝 样本 {i+1}/{num_samples}")
        input("按回车键开始录制...")
        
        audio = await record_audio(duration=5.0)
        audio_samples.append(audio)
        
        print(f"✅ 样本 {i+1} 录制成功 ({len(audio)} 采样点)")
    
    # 注册说话人
    print("\n" + "=" * 50)
    print("正在注册声纹...")
    await model.register_speaker(speaker_id, audio_samples)
    print(f"✅ 说话人 [{speaker_id}] 注册成功！")
    
    # 测试识别
    print("\n" + "=" * 50)
    print("测试声纹识别...")
    test_audio = audio_samples[0]
    recognized = await model.recognize(test_audio)
    print(f"识别结果: {recognized}")
    
    if recognized == speaker_id:
        print("✅ 声纹识别测试通过！")
    else:
        print("⚠️  声纹识别测试未通过，建议重新注册")
    
    # 关闭模型
    await model.close()
    
    print("\n" + "=" * 50)
    print("声纹注册完成！")
    print(f"数据库文件: {Path('speaker_db.json').absolute()}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
