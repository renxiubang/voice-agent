"""
测试各个模块
"""
import asyncio
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_config_loader():
    """测试配置加载器"""
    logger.info("=" * 50)
    logger.info("测试 配置加载器")
    logger.info("=" * 50)
    
    try:
        from utils.config_loader import load_config
        
        config = load_config()
        assert isinstance(config, dict)
        assert "gateway" in config
        assert "auditory" in config
        assert "cognition" in config
        assert "tts" in config
        
        logger.info("✓ 配置加载器测试通过")
        return True
        
    except Exception as e:
        logger.error(f"✗ 配置加载器测试失败: {e}")
        return False


async def test_queues():
    """测试队列管理器"""
    logger.info("=" * 50)
    logger.info("测试 队列管理器")
    logger.info("=" * 50)
    
    try:
        from core.queues import (
            get_audio_queue,
            get_text_queue,
            get_llm_queue,
            get_tts_queue
        )
        
        # 测试音频队列
        audio_queue = get_audio_queue()
        await audio_queue.put(b"test audio")
        data = await audio_queue.get()
        assert data == b"test audio"
        
        # 测试文本队列
        text_queue = get_text_queue()
        await text_queue.put("测试文本")
        text = await text_queue.get()
        assert text == "测试文本"
        
        logger.info("✓ 队列管理器测试通过")
        return True
        
    except Exception as e:
        logger.error(f"✗ 队列管理器测试失败: {e}")
        return False


async def test_vad():
    """测试 VAD 模型"""
    logger.info("=" * 50)
    logger.info("测试 VAD 模型")
    logger.info("=" * 50)
    
    try:
        from auditory.vad import VADModel
        from utils.config_loader import load_config
        
        config = load_config()
        vad_model = VADModel(config["auditory"])
        
        # 加载模型 (可能需要下载)
        logger.info("正在加载 VAD 模型 (首次运行会下载)...")
        await vad_model.load_model()
        
        # 生成测试音频
        import numpy as np
        sample_rate = 16000
        t = np.linspace(0, 1, sample_rate)
        test_audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        
        # 测试语音检测
        is_speech = await vad_model.is_speech(test_audio)
        
        logger.info(f"✓ VAD 模型测试通过 (is_speech={is_speech})")
        return True
        
    except Exception as e:
        logger.error(f"✗ VAD 模型测试失败: {e}")
        return False


async def test_asr():
    """测试 ASR 模型"""
    logger.info("=" * 50)
    logger.info("测试 ASR 模型")
    logger.info("=" * 50)
    
    try:
        from auditory.asr import ASRModel
        from utils.config_loader import load_config
        
        config = load_config()
        asr_model = ASRModel(config["auditory"])
        
        # 加载模型 (可能需要下载)
        logger.info("正在加载 ASR 模型 (首次运行会下载)...")
        await asr_model.load_model()
        
        logger.info("✓ ASR 模型加载成功")
        return True
        
    except Exception as e:
        logger.error(f"✗ ASR 模型测试失败: {e}")
        return False


async def test_speaker_recognition():
    """测试声纹识别模型"""
    logger.info("=" * 50)
    logger.info("测试 声纹识别模型")
    logger.info("=" * 50)
    
    try:
        from auditory.speaker_recognition import SpeakerRecognitionModel
        from utils.config_loader import load_config
        
        config = load_config()
        model = SpeakerRecognitionModel(config["auditory"])
        
        # 加载模型 (可能需要下载)
        logger.info("正在加载声纹识别模型 (首次运行会下载)...")
        await model.load_model()
        
        logger.info("✓ 声纹识别模型加载成功")
        return True
        
    except Exception as e:
        logger.error(f"✗ 声纹识别模型测试失败: {e}")
        return False


async def test_tts():
    """测试 TTS 模型"""
    logger.info("=" * 50)
    logger.info("测试 TTS 模型")
    logger.info("=" * 50)
    
    try:
        from tts.piper_tts import PiperTTSModel
        from utils.config_loader import load_config
        
        config = load_config()
        tts_model = PiperTTSModel(config["tts"])
        
        # 加载模型 (可能需要下载)
        logger.info("正在加载 TTS 模型 (首次运行会下载)...")
        await tts_model.load_model()
        
        logger.info("✓ TTS 模型加载成功")
        return True
        
    except Exception as e:
        logger.error(f"✗ TTS 模型测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    logger.info("\n" + "=" * 50)
    logger.info("智能体语音对话系统 - 模块测试")
    logger.info("=" * 50 + "\n")
    
    results = []
    
    # 测试配置加载器
    result = await test_config_loader()
    results.append(("配置加载器", result))
    
    # 测试队列管理器
    result = await test_queues()
    results.append(("队列管理器", result))
    
    # 测试 VAD 模型
    result = await test_vad()
    results.append(("VAD 模型", result))
    
    # 测试 ASR 模型
    result = await test_asr()
    results.append(("ASR 模型", result))
    
    # 测试声纹识别模型
    result = await test_speaker_recognition()
    results.append(("声纹识别模型", result))
    
    # 测试 TTS 模型
    result = await test_tts()
    results.append(("TTS 模型", result))
    
    # 输出测试结果
    logger.info("\n" + "=" * 50)
    logger.info("测试结果汇总")
    logger.info("=" * 50)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        logger.info(f"{name}: {status}")
    
    # 检查是否所有测试通过
    all_passed = all(result for _, result in results)
    
    if all_passed:
        logger.info("\n✓ 所有测试通过!")
        return 0
    else:
        logger.error("\n✗ 部分测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
