"""
pyannote.audio 声纹识别模型
"""
import torch
import numpy as np
import logging
from typing import Optional, Dict
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SpeakerRecognitionModel:
    """
    声纹识别模型
    支持声纹注册和识别
    """
    
    def __init__(self, config: dict):
        """
        初始化声纹识别模型
        
        Args:
            config: 听觉层配置
        """
        self.config = config
        self.model = None
        self.similarity_threshold = config.get("similarity_threshold", 0.7)
        
        # 声纹数据库 (内存中，实际应用中应使用数据库)
        self.speaker_db: Dict[str, np.ndarray] = {}
        self.db_path = Path("speaker_db.json")
        
        # 加载声纹数据库
        self._load_db()
    
    async def load_model(self):
        """加载 pyannote.audio 模型"""
        logger.info("正在加载 pyannote.audio 声纹识别模型...")
        
        try:
            # 加载 embedding 模型
            from pyannote.audio import Model
            from pyannote.audio.tasks import SpeakerEmbedding
            from pyannote.audio.models import SpeakerEmbedding as EmbeddingModel
            
            # 使用预训练的 embedding 模型
            model = Model.from_pretrained(
                "pyannote/embedding",
                strict=False
            )
            
            self.model = model
            logger.info("pyannote.audio 声纹识别模型加载成功")
            
        except Exception as e:
            logger.error(f"加载 pyannote.audio 模型失败: {e}")
            raise
    
    async def extract_embedding(self, audio: np.ndarray) -> np.ndarray:
        """
        提取音频的声纹特征
        
        Args:
            audio: 音频数据 (numpy 数组, float32, -1.0 ~ 1.0)
            
        Returns:
            声纹特征向量 (numpy 数组)
        """
        if self.model is None:
            raise RuntimeError("声纹识别模型未加载")
        
        try:
            # 转换为 torch tensor
            audio_tensor = torch.from_numpy(audio).unsqueeze(0)  # (1, T)
            
            # 提取 embedding
            with torch.no_grad():
                embedding = self.model(audio_tensor)
            
            # 转换为 numpy 数组
            embedding_np = embedding.squeeze().numpy()
            
            return embedding_np
            
        except Exception as e:
            logger.error(f"提取声纹特征失败: {e}")
            raise
    
    async def register_speaker(self, speaker_id: str, audio_samples: list):
        """
        注册说话人
        
        Args:
            speaker_id: 说话人 ID
            audio_samples: 音频样本列表 (每个元素是 numpy 数组)
        """
        logger.info(f"正在注册说话人: {speaker_id}")
        
        # 提取所有样本的 embedding
        embeddings = []
        for audio in audio_samples:
            embedding = await self.extract_embedding(audio)
            embeddings.append(embedding)
        
        # 计算平均 embedding
        avg_embedding = np.mean(embeddings, axis=0)
        
        # 保存到数据库
        self.speaker_db[speaker_id] = avg_embedding
        self._save_db()
        
        logger.info(f"说话人 {speaker_id} 注册成功")
    
    async def recognize(self, audio: np.ndarray) -> str:
        """
        识别说话人
        
        Args:
            audio: 音频数据 (numpy 数组)
            
        Returns:
            说话人 ID，如果未识别到则返回 "unknown"
        """
        if len(self.speaker_db) == 0:
            # 如果数据库为空，返回 target_speaker
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
                
                if similarity > max_similarity:
                    max_similarity = similarity
                    recognized_speaker = speaker_id
            
            # 如果相似度超过阈值，返回识别结果
            if max_similarity >= self.similarity_threshold:
                logger.info(f"识别到说话人: {recognized_speaker} (相似度: {max_similarity:.3f})")
                return recognized_speaker
            else:
                logger.info(f"未识别到已知说话人 (最大相似度: {max_similarity:.3f})")
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
            
            logger.info(f"声纹数据库已保存到 {self.db_path}")
            
        except Exception as e:
            logger.error(f"保存声纹数据库失败: {e}")
    
    def _load_db(self):
        """从文件加载声纹数据库"""
        try:
            if self.db_path.exists():
                with open(self.db_path, "r", encoding="utf-8") as f:
                    db_dict = json.load(f)
                
                # 将列表转换为 numpy 数组
                for speaker_id, embedding_list in db_dict.items():
                    self.speaker_db[speaker_id] = np.array(embedding_list)
                
                logger.info(f"声纹数据库已从 {self.db_path} 加载")
            else:
                logger.info("声纹数据库文件不存在，使用空数据库")
                
        except Exception as e:
            logger.error(f"加载声纹数据库失败: {e}")


if __name__ == "__main__":
    # 测试声纹识别模型
    import asyncio
    import soundfile as sf
    
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
        
        # 注册说话人
        await model.register_speaker("target_speaker", [test_audio])
        
        # 识别说话人
        recognized = await model.recognize(test_audio)
        print(f"识别结果: {recognized}")
    
    asyncio.run(test_speaker_recognition())
