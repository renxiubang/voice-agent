"""
声纹识别模型
使用 pyannote.audio 提取专业声纹嵌入向量
从 ModelScope 下载模型（国内镜像）
"""
import numpy as np
import logging
from typing import Dict, Optional, List
from pathlib import Path
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
import io
import wave

# 设置环境变量，优先使用 ModelScope
os.environ["MODELSCOPE_CACHE"] = os.path.expanduser("~/.cache/modelscope")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SpeakerRecognitionModel:
    """
    声纹识别模型
    使用 pyannote.audio 提取专业声纹嵌入向量
    """
    
    def __init__(self, config: dict):
        """
        初始化声纹识别模型
        
        Args:
            config: 听觉层配置
        """
        self.config = config
        self.similarity_threshold = config.get("similarity_threshold", 0.7)
        
        # pyannote.audio 模型
        self.inference = None
        self.model_name = config.get("speaker_embedding_model", "pyannote/embedding")
        
        # 线程池（用于运行 pyannote.audio 模型，避免阻塞主事件循环）
        self.executor = ThreadPoolExecutor(max_workers=1)
        
        # 声纹数据库
        self.speaker_db: Dict[str, np.ndarray] = {}
        self.db_path = Path("speaker_db.json")
        
        # 加载声纹数据库
        self._load_db()
        
        logger.info(f"声纹识别模型初始化: model={self.model_name}")
    
    async def load_model(self):
        """加载 pyannote.audio 声纹识别模型"""
        try:
            logger.info(f"正在加载声纹识别模型: {self.model_name}")
            
            # 在单独线程中加载模型，避免阻塞主事件循环
            loop = asyncio.get_event_loop()
            self.inference = await loop.run_in_executor(
                self.executor,
                self._load_embedding_model
            )
            
            logger.info("✅ 声纹识别模型加载成功")
            
        except Exception as e:
            logger.error(f"❌ 加载声纹识别模型失败: {e}")
            raise
    
    def _load_embedding_model(self):
        """
        加载 pyannote.audio SpeakerEmbedding 模型（在线程池中运行）
        使用 ModelScope 下载模型
        
        Returns:
            Inference 对象
        """
        try:
            from modelscope import snapshot_download
            from pyannote.audio import Model, Inference
            
            # 从 ModelScope 下载模型
            logger.info(f"正在从 ModelScope 下载模型: {self.model_name}")
            model_dir = snapshot_download(self.model_name)
            logger.info(f"模型已下载到: {model_dir}")
            
            # 加载模型
            model = Model.from_pretrained(model_dir)
            
            # 创建 Inference 对象
            inference = Inference(model, window="whole")
            
            logger.info(f"✅ SpeakerEmbedding 模型已加载: {self.model_name}")
            return inference
            
        except Exception as e:
            logger.error(f"加载 SpeakerEmbedding 模型失败: {e}")
            raise
    
    async def extract_embedding(self, audio: np.ndarray) -> np.ndarray:
        """
        提取音频的声纹特征（使用 pyannote.audio）
        
        Args:
            audio: 音频数据 (numpy 数组, float32, -1.0 ~ 1.0)
            
        Returns:
            声纹特征向量 (numpy 数组)
        """
        if self.inference is None:
            raise RuntimeError("声纹识别模型未加载，请先调用 load_model()")
        
        try:
            # 将音频数据转换为 pyannote.audio 所需的格式
            # 保存为临时 WAV 文件（pyannote.audio 需要文件输入）
            
            # 确保音频数据是一维数组
            if len(audio.shape) > 1:
                audio = audio.squeeze()
            
            # 在单独线程中运行模型推理，避免阻塞主事件循环
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                self.executor,
                self._extract_embedding_sync,
                audio
            )
            
            return embedding
            
        except Exception as e:
            logger.error(f"提取声纹特征失败: {e}")
            raise
    
    def _extract_embedding_sync(self, audio: np.ndarray) -> np.ndarray:
        """
        同步提取声纹特征（在线程池中运行）
        
        Args:
            audio: 音频数据 (numpy 数组, float32, -1.0 ~ 1.0)
            
        Returns:
            声纹特征向量 (numpy 数组)
        """
        try:
            # 将音频保存为临时文件
            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(16000)  # 16kHz
                audio_int16 = (audio * 32767).astype(np.int16)
                wav_file.writeframes(audio_int16.tobytes())
            
            buffer.seek(0)
            
            # 使用 pyannote.audio Inference 提取嵌入向量
            # inference 对象接受类文件对象或文件路径
            embedding = self.inference(buffer)
            
            # 确保返回的是 numpy 数组
            if not isinstance(embedding, np.ndarray):
                embedding = np.array(embedding)
            
            logger.debug(f"声纹特征提取成功: shape={embedding.shape}")
            return embedding
            
        except Exception as e:
            logger.error(f"同步提取声纹特征失败: {e}")
            raise
    
    async def register_speaker(self, speaker_id: str, audio_samples: List[np.ndarray]):
        """
        注册说话人
        
        Args:
            speaker_id: 说话人 ID
            audio_samples: 音频样本列表 (每个元素是 numpy 数组)
        """
        logger.info(f"正在注册说话人: {speaker_id}")
        
        try:
            # 提取所有样本的 embedding
            embeddings = []
            for i, audio in enumerate(audio_samples):
                logger.debug(f"提取第 {i+1}/{len(audio_samples)} 个样本的声纹特征...")
                embedding = await self.extract_embedding(audio)
                embeddings.append(embedding)
            
            # 计算平均 embedding
            avg_embedding = np.mean(embeddings, axis=0)
            
            # 保存到数据库
            self.speaker_db[speaker_id] = avg_embedding
            self._save_db()
            
            logger.info(f"✅ 说话人 {speaker_id} 注册成功（使用了 {len(audio_samples)} 个样本）")
            
        except Exception as e:
            logger.error(f"❌ 注册说话人 {speaker_id} 失败: {e}")
            raise
    
    async def recognize(self, audio: np.ndarray) -> str:
        """
        识别说话人
        
        Args:
            audio: 音频数据 (numpy 数组, float32, -1.0 ~ 1.0)
            
        Returns:
            说话人 ID，如果未识别到则返回 "unknown"
        """
        if len(self.speaker_db) == 0:
            # 如果数据库为空，返回 target_speaker（默认行为）
            logger.warning("声纹数据库为空，返回默认说话人: target_speaker")
            return "target_speaker"
        
        try:
            # 提取音频的 embedding
            embedding = await self.extract_embedding(audio)
            
            # 与数据库中的所有说话人比较
            max_similarity = -1
            recognized_speaker = "unknown"
            
            for speaker_id, db_embedding in self.speaker_db.items():
                # 计算余弦相似度
                similarity = self._cosine_similarity(embedding, db_embedding)
                
                logger.debug(f"与说话人 {speaker_id} 的相似度: {similarity:.3f}")
                
                if similarity > max_similarity:
                    max_similarity = similarity
                    recognized_speaker = speaker_id
            
            # 如果相似度超过阈值，返回识别结果
            if max_similarity >= self.similarity_threshold:
                logger.info(f"✅ 识别到说话人: {recognized_speaker} (相似度: {max_similarity:.3f})")
                return recognized_speaker
            else:
                logger.info(f"❌ 未识别到已知说话人 (最大相似度: {max_similarity:.3f} < 阈值 {self.similarity_threshold})")
                return "unknown"
            
        except Exception as e:
            logger.error(f"声纹识别失败: {e}")
            return "unknown"
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """
        计算余弦相似度
        
        Args:
            a: 向量 a
            b: 向量 b
            
        Returns:
            余弦相似度 (-1 ~ 1)
        """
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    def _save_db(self):
        """保存声纹数据库到文件"""
        try:
            # 将 numpy 数组转换为列表
            db_dict = {}
            for speaker_id, embedding in self.speaker_db.items():
                db_dict[speaker_id] = embedding.tolist()
            
            # 保存到 JSON 文件
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(db_dict, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 声纹数据库已保存到 {self.db_path}")
            
        except Exception as e:
            logger.error(f"❌ 保存声纹数据库失败: {e}")
    
    def _load_db(self):
        """从文件加载声纹数据库"""
        try:
            if self.db_path.exists():
                with open(self.db_path, "r", encoding="utf-8") as f:
                    db_dict = json.load(f)
                
                # 将列表转换为 numpy 数组
                for speaker_id, embedding_list in db_dict.items():
                    self.speaker_db[speaker_id] = np.array(embedding_list)
                
                logger.info(f"✅ 声纹数据库已从 {self.db_path} 加载（{len(self.speaker_db)} 个说话人）")
            else:
                logger.info("声纹数据库文件不存在，使用空数据库")
                
        except Exception as e:
            logger.error(f"❌ 加载声纹数据库失败: {e}")
    
    async def close(self):
        """关闭模型，释放资源"""
        try:
            if self.executor:
                self.executor.shutdown(wait=True)
                logger.info("✅ 线程池已关闭")
        except Exception as e:
            logger.error(f"关闭模型失败: {e}")


if __name__ == "__main__":
    # 测试声纹识别模型
    async def test_speaker_recognition():
        # 加载配置
        from utils.config_loader import load_config
        config = load_config()
        auditory_config = config["auditory"]
        
        # 创建声纹识别模型
        model = SpeakerRecognitionModel(auditory_config)
        await model.load_model()
        
        # 生成测试音频 (1秒，440Hz 正弦波)
        sample_rate = 16000
        t = np.linspace(0, 1, sample_rate)
        test_audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        
        # 注册说话人（使用多个样本）
        audio_samples = [test_audio, test_audio * 0.9, test_audio * 1.1]
        await model.register_speaker("target_speaker", audio_samples)
        
        # 识别说话人
        recognized = await model.recognize(test_audio)
        print(f"识别结果: {recognized}")
        
        # 关闭模型
        await model.close()
    
    asyncio.run(test_speaker_recognition())
