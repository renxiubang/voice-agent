"""
Piper TTS 模型
"""
import subprocess
import numpy as np
import logging
from pathlib import Path
from typing import Optional
import tempfile
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PiperTTSModel:
    """
    Piper TTS 模型
    本地神经网络 TTS 引擎
    """
    
    def __init__(self, config: dict):
        """
        初始化 Piper TTS 模型
        
        Args:
            config: 发声层配置
        """
        self.config = config
        self.model_name = config.get("model", "zh_CN-huayan-medium")
        self.sample_rate = config.get("sample_rate", 22050)
        self.buffer_size = config.get("buffer_size", 20)
        
        # Piper 可执行文件路径
        self.piper_path = "piper"
        self.model_path = None
        
    async def load_model(self):
        """加载 Piper TTS 模型"""
        logger.info(f"正在加载 Piper TTS 模型: {self.model_name}")
        
        try:
            # 检查 piper 是否安装
            result = subprocess.run(
                ["which", self.piper_path],
                capture_output=True,
                text=True
            )
            
            if result.returncode!= 0:
                logger.error("Piper TTS 未安装，请运行: pip install piper-tts")
                raise RuntimeError("Piper TTS 未安装")
            
            # 下载模型 (如果不存在)
            self.model_path = await self._download_model()
            
            logger.info(f"Piper TTS 模型加载成功: {self.model_path}")
            
        except Exception as e:
            logger.error(f"加载 Piper TTS 模型失败: {e}")
            raise
    
    async def _download_model(self) -> Path:
        """
        下载 Piper TTS 模型
        
        Returns:
            模型文件路径
        """
        # 模型缓存目录
        cache_dir = Path.home() / ".local" / "share" / "piper" / "models"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 模型文件名
        model_file = cache_dir / f"{self.model_name}.onnx"
        
        # 如果模型已存在，直接返回
        if model_file.exists():
            logger.info(f"模型已存在: {model_file}")
            return model_file
        
        # 下载模型
        logger.info(f"正在下载模型: {self.model_name}")
        
        try:
            # 使用 piper 下载模型
            result = subprocess.run(
                [self.piper_path, "--download-model", self.model_name],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info(f"模型下载成功: {model_file}")
                return model_file
            else:
                logger.error(f"模型下载失败: {result.stderr}")
                raise RuntimeError(f"模型下载失败: {result.stderr}")
                
        except Exception as e:
            logger.error(f"下载模型失败: {e}")
            raise
    
    async def synthesize(self, text: str) -> bytes:
        """
        语音合成
        
        Args:
            text: 输入文本
            
        Returns:
            音频数据 (PCM 16-bit, sample_rate Hz, mono)
        """
        if self.model_path is None:
            raise RuntimeError("TTS 模型未加载")
        
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                output_path = f.name
            
            # 使用 piper 合成语音
            process = subprocess.Popen(
                [self.piper_path, "--model", str(self.model_path), "--output_file", output_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # 输入文本
            stdout, stderr = process.communicate(input=text.encode("utf-8"))
            
            if process.returncode!= 0:
                logger.error(f"TTS 合成失败: {stderr.decode('utf-8')}")
                raise RuntimeError(f"TTS 合成失败: {stderr.decode('utf-8')}")
            
            # 读取生成的 WAV 文件
            import wave
            with wave.open(output_path, "rb") as wav_file:
                # 读取音频数据
                audio_frames = wav_file.readframes(wav_file.getnframes())
                
                # 转换为 numpy 数组
                audio_int16 = np.frombuffer(audio_frames, dtype=np.int16)
                
                # 转换为 bytes
                audio_bytes = audio_int16.tobytes()
            
            # 删除临时文件
            os.unlink(output_path)
            
            logger.info(f"TTS 合成完成: {len(text)} 字符 -> {len(audio_bytes)} 字节")
            return audio_bytes
            
        except Exception as e:
            logger.error(f"TTS 合成失败: {e}")
            return b""
    
    async def synthesize_stream(self, text_stream: list) -> bytes:
        """
        流式语音合成 (拼接多个文本片段的音频)
        
        Args:
            text_stream: 文本流 (字符串列表)
            
        Returns:
            拼接后的音频数据 (PCM 16-bit)
        """
        audio_segments = []
        
        for text in text_stream:
            audio_segment = await self.synthesize(text)
            audio_segments.append(audio_segment)
        
        # 拼接所有音频片段
        combined_audio = b"".join(audio_segments)
        
        logger.info(f"流式 TTS 合成完成: {len(text_stream)} 片段 -> {len(combined_audio)} 字节")
        return combined_audio


if __name__ == "__main__":
    # 测试 Piper TTS 模型
    import asyncio
    
    async def test_piper_tts():
        # 加载配置
        from utils.config_loader import load_config
        config = load_config()
        tts_config = config["tts"]
        
        # 创建 Piper TTS 模型
        tts_model = PiperTTSModel(tts_config)
        await tts_model.load_model()
        
        # 测试语音合成
        test_text = "你好，我是一个智能助手。"
        print(f"输入文本: {test_text}")
        
        audio_bytes = await tts_model.synthesize(test_text)
        print(f"生成音频: {len(audio_bytes)} 字节")
        
        # 保存为 WAV 文件
        import wave
        output_path = "test_tts_output.wav"
        with wave.open(output_path, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(tts_model.sample_rate)
            wav_file.writeframes(audio_bytes)
        
        print(f"音频已保存到: {output_path}")
    
    asyncio.run(test_piper_tts())
