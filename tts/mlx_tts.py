"""
MLX-Audio + Kokoro TTS 模型
真正的流式输出（逐块生成音频）
"""
# 必须在所有 import 之前设置，否则 huggingface_hub 可能已缓存默认值
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import numpy as np
import logging
from pathlib import Path
from typing import AsyncGenerator, Optional, Iterator
import wave
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MLXTTSModel:
    """
    MLX-Audio TTS 模型（使用 Kokoro 后端）
    支持真正的流式输出
    """
    
    def __init__(self, config: dict):
        """
        初始化 MLX-Audio TTS 模型
        
        Args:
            config: TTS 配置
        """
        self.config = config
        self.model_name = config.get("model", "mlx-community/Kokoro-82M-bf16")
        self.voice = config.get("voice", "zf_xiaobei")  # 默认中文女声
        self.lang_code = config.get("lang_code", "z")    # z = 中文
        self.speed = config.get("speed", 1.0)
        self.sample_rate = config.get("sample_rate", 24000)  # Kokoro 输出 24kHz
        
        self.model = None
        
    async def load_model(self):
        """加载 MLX-Audio TTS 模型"""
        logger.info(f"正在加载 MLX-Audio TTS 模型: {self.model_name}")
        
        try:
            from mlx_audio.tts.utils import load_model
            
            # 加载模型（支持 bf16, 8bit, 4bit）
            self.model = load_model(self.model_name)
            
            logger.info(f"MLX-Audio TTS 模型加载成功: {self.model_name}")
            logger.info(f"  声音: {self.voice}, 语言: {self.lang_code}, 语速: {self.speed}")
            
        except Exception as e:
            logger.error(f"加载 MLX-Audio TTS 模型失败: {e}")
            raise
    
    def _mxarray_to_bytes(self, mx_array) -> bytes:
        """
        将 MLX 数组转换为 PCM bytes
        
        Args:
            mx_array: MLX 数组 (float32, range [-1, 1])
            
        Returns:
            PCM 16-bit bytes (little-endian)
        """
        # 转换为 numpy 数组
        import numpy as np
        audio_np = np.array(mx_array, dtype=np.float32)
        
        # 归一化到 [-1, 1] (如果不在范围内)
        max_val = np.max(np.abs(audio_np))
        if max_val > 1.0:
            audio_np = audio_np / max_val
        
        # 转换为 16-bit PCM
        audio_int16 = (audio_np * 32767).astype(np.int16)
        
        # 转换为 bytes
        return audio_int16.tobytes()
    
    async def synthesize(self, text: str) -> bytes:
        """
        语音合成（完整输出）
        
        Args:
            text: 输入文本
            
        Returns:
            完整音频数据 (PCM 16-bit, 24kHz, mono)
        """
        if self.model is None:
            raise RuntimeError("TTS 模型未加载")
        
        try:
            logger.info(f"TTS 合成开始: {text[:50]}...")
            
            # 收集所有音频片段
            audio_segments = []
            for result in self.model.generate(
                text=text,
                voice=self.voice,
                speed=self.speed,
                lang_code=self.lang_code,
            ):
                audio_segment = self._mxarray_to_bytes(result.audio)
                audio_segments.append(audio_segment)
            
            # 拼接所有片段
            combined_audio = b"".join(audio_segments)
            
            logger.info(f"TTS 合成完成: {len(text)} 字符 -> {len(combined_audio)} 字节")
            return combined_audio
            
        except Exception as e:
            logger.error(f"TTS 合成失败: {e}")
            return b""
    
    async def synthesize_stream(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        流式语音合成（真正的流式输出）
        
        每次 yield 一个音频片段，不需要等待全部合成完毕
        
        Args:
            text: 输入文本
            
        Yields:
            音频数据块 (PCM 16-bit, 24kHz, mono)
        """
        if self.model is None:
            raise RuntimeError("TTS 模型未加载")
        
        try:
            logger.info(f"TTS 流式合成开始: {text[:50]}...")
            
            chunk_count = 0
            total_bytes = 0
            
            # model.generate() 本身是迭代器，逐块生成音频
            for result in self.model.generate(
                text=text,
                voice=self.voice,
                speed=self.speed,
                lang_code=self.lang_code,
            ):
                # 转换为 PCM bytes
                audio_chunk = self._mxarray_to_bytes(result.audio)
                
                chunk_count += 1
                total_bytes += len(audio_chunk)
                
                logger.debug(f"TTS 流式输出: 块 {chunk_count}, {len(audio_chunk)} 字节")
                
                # 立即 yield 这个音频块（真正的流式输出）
                yield audio_chunk
            
            logger.info(f"TTS 流式合成完成: {chunk_count} 块 -> {total_bytes} 字节")
            
        except Exception as e:
            logger.error(f"TTS 流式合成失败: {e}")
            raise
    
    async def synthesize_from_tokens(self, tokens: list) -> AsyncGenerator[bytes, None]:
        """
        从 token 列表流式合成（适用于 LLM token 流式输出场景）
        
        Args:
            tokens: LLM 生成的 token 列表（逐个传入）
            
        Yields:
            音频数据块
        """
        if self.model is None:
            raise RuntimeError("TTS 模型未加载")
        
        # 将 tokens 组合成文本
        text = "".join(tokens)
        
        # 使用流式合成
        async for audio_chunk in self.synthesize_stream(text):
            yield audio_chunk


async def test_mlx_tts():
    """测试 MLX-Audio TTS"""
    import asyncio
    
    # 配置
    config = {
        "model": "mlx-community/Kokoro-82M-bf16",
        "voice": "zf_xiaobei",
        "lang_code": "z",
        "speed": 1.0,
        "sample_rate": 24000,
    }
    
    # 创建 TTS 模型
    tts_model = MLXTTSModel(config)
    await tts_model.load_model()
    
    # 测试完整合成
    test_text = "你好，我是一个智能助手。很高兴为你服务！"
    print(f"输入文本: {test_text}")
    
    audio_bytes = await tts_model.synthesize(test_text)
    print(f"完整合成: {len(audio_bytes)} 字节")
    
    # 保存为 WAV 文件
    output_path = "test_mlx_tts_output.wav"
    with wave.open(output_path, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(tts_model.sample_rate)
        wav_file.writeframes(audio_bytes)
    
    print(f"音频已保存到: {output_path}")
    
    # 测试流式合成
    print("\n测试流式合成...")
    chunk_count = 0
    async for audio_chunk in tts_model.synthesize_stream(test_text):
        chunk_count += 1
        print(f"  收到第 {chunk_count} 块音频: {len(audio_chunk)} 字节")
    
    print(f"流式合成完成: 共 {chunk_count} 块")


if __name__ == "__main__":
    asyncio.run(test_mlx_tts())
