"""
LLM 推理模型
支持本地模式 (mlx-lm) 和 API 模式 (OpenAI 兼容)
"""
import logging
from typing import AsyncGenerator, Optional
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMModel:
    """
    LLM 模型
    支持两种模式:
    - local: 使用 Apple MLX LLM (mlx-lm)
    - api: 使用 OpenAI 兼容 API
    """
    
    def __init__(self, config: dict):
        """
        初始化 LLM 模型
        
        Args:
            config: 认知层配置
        """
        self.config = config
        self.mode = config.get("llm_mode", "api")  # "local" 或 "api"
        
        # API 模式配置
        self.api_base = config.get("llm_api_base", "http://127.0.0.1:8000/v1")
        self.api_key = config.get("llm_api_key", "dummy")
        self.api_model = config.get("llm_model", "Qwen3.5-9B-MLX-4bit")
        
        # 本地模式配置
        self.local_model = config.get("llm_local_model", "mistralai/Mistral-7B-Instruct-v0.3")
        
        # 通用配置
        self.max_tokens = config.get("max_tokens", 512)
        self.temperature = config.get("temperature", 0.7)
        self.system_prompt = config.get("system_prompt", "你是一个智能助手，请用简洁明了的中文回答。")
        
        # 本地模式组件
        self.model = None
        self.tokenizer = None
        
        # API 模式客户端
        self.client = None
    
    async def load_model(self):
        """加载 LLM 模型"""
        if self.mode == "api":
            await self._load_model_api()
        else:
            await self._load_model_local()
    
    async def _load_model_api(self):
        """加载 API 模式"""
        logger.info(f"LLM 使用 API 模式: {self.api_base}")
        logger.info(f"API 模型: {self.api_model}")
        
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(base_url=self.api_base, api_key=self.api_key)
            
            # 测试连接
            try:
                models = await self.client.models.list()
                logger.info(f"API 连接成功，可用模型: {[m.id for m in models.data]}")
            except Exception as e:
                logger.warning(f"API 连接测试失败: {e}，将继续使用")
                
        except ImportError:
            logger.error("openai 库未安装，请运行: pip install openai")
            raise
    
    async def _load_model_local(self):
        """加载本地 MLX LLM 模式"""
        logger.info(f"正在加载 LLM 本地模型: {self.local_model}")
        
        try:
            from mlx_lm import load, generate
            
            self.model, self.tokenizer = load(self.local_model)
            logger.info(f"LLM 本地模型 {self.local_model} 加载成功")
            
        except ImportError:
            logger.error("mlx-lm 未安装，请运行: pip install mlx-lm")
            raise
        except Exception as e:
            logger.error(f"加载 LLM 模型失败: {e}")
            raise
    
    async def generate_stream(self, text: str) -> AsyncGenerator[str, None]:
        """
        流式生成回复
        
        Args:
            text: 输入文本
            
        Yields:
            生成的 token (字符串)
        """
        if self.mode == "api":
            async for token in self._generate_stream_api(text):
                yield token
        else:
            async for token in self._generate_stream_local(text):
                yield token
    
    async def _generate_stream_api(self, text: str) -> AsyncGenerator[str, None]:
        """API 模式流式生成"""
        if self.client is None:
            raise RuntimeError("API 客户端未初始化")
        
        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": text}
            ]
            
            response = await self.client.chat.completions.create(
                model=self.api_model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=True
            )
            
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            
            logger.info("API 流式生成完成")
            
        except Exception as e:
            logger.error(f"API 生成失败: {e}")
            raise
    
    async def _generate_stream_local(self, text: str) -> AsyncGenerator[str, None]:
        """本地模式流式生成"""
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("LLM 模型未加载")
        
        try:
            from mlx_lm import generate
            
            # 构建提示词
            prompt = f"<s>[INST] {self.system_prompt}\n\n{text} [/INST]"
            
            generated_tokens = []
            for token_id in generate(
                self.model,
                self.tokenizer,
                prompt,
                max_tokens=self.max_tokens,
                temp=self.temperature,
                verbose=False
            ):
                token = self.tokenizer.decode([token_id])
                generated_tokens.append(token_id)
                yield token
            
            logger.info(f"本地 LLM 生成完成: {len(generated_tokens)} tokens")
            
        except Exception as e:
            logger.error(f"本地 LLM 生成失败: {e}")
            raise
    
    async def generate(self, text: str) -> str:
        """
        生成回复 (非流式)
        
        Args:
            text: 输入文本
            
        Returns:
            生成的回复 (字符串)
        """
        tokens = []
        async for token in self.generate_stream(text):
            tokens.append(token)
        
        return "".join(tokens)


if __name__ == "__main__":
    # 测试 LLM 模型
    import asyncio
    
    async def test_llm():
        # 加载配置
        from utils.config_loader import load_config
        config = load_config()
        cognition_config = config["cognition"]
        
        # 创建 LLM 模型
        llm_model = LLMModel(cognition_config)
        await llm_model.load_model()
        
        # 测试流式生成
        test_text = "你好，请介绍一下你自己。"
        print(f"输入: {test_text}")
        print("输出: ", end="", flush=True)
        
        async for token in llm_model.generate_stream(test_text):
            print(token, end="", flush=True)
        
        print()  # 换行
    
    asyncio.run(test_llm())
