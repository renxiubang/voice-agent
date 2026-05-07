"""
异步队列定义
"""
import asyncio
from typing import Optional


class QueueManager:
    """
    队列管理器（单例模式）
    管理各个模块间的 asyncio.Queue
    """
    _instance: Optional["QueueManager"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # 音频流队列 (从网关层到听觉层)
        self.audio_queue = asyncio.Queue(maxsize=10)
        
        # 识别文本队列 (从听觉层到认知层)
        self.text_queue = asyncio.Queue(maxsize=10)
        
        # LLM 输出队列 (从认知层到发声层)
        self.llm_queue = asyncio.Queue(maxsize=100)
        
        # TTS 音频流队列 (从发声层到网关层)
        self.tts_queue = asyncio.Queue(maxsize=10)
        
        self._initialized = True
    
    def get_audio_queue(self) -> asyncio.Queue:
        """获取音频流队列"""
        return self.audio_queue
    
    def get_text_queue(self) -> asyncio.Queue:
        """获取识别文本队列"""
        return self.text_queue
    
    def get_llm_queue(self) -> asyncio.Queue:
        """获取 LLM 输出队列"""
        return self.llm_queue
    
    def get_tts_queue(self) -> asyncio.Queue:
        """获取 TTS 音频流队列"""
        return self.tts_queue
    
    def clear_all(self):
        """清空所有队列"""
        for queue in [self.audio_queue, self.text_queue, 
                     self.llm_queue, self.tts_queue]:
            while not queue.empty():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break


# 全局队列管理器实例
queue_manager = QueueManager()


# 导出便捷函数
def get_audio_queue() -> asyncio.Queue:
    return queue_manager.get_audio_queue()


def get_text_queue() -> asyncio.Queue:
    return queue_manager.get_text_queue()


def get_llm_queue() -> asyncio.Queue:
    return queue_manager.get_llm_queue()


def get_tts_queue() -> asyncio.Queue:
    return queue_manager.get_tts_queue()


def clear_all_queues():
    queue_manager.clear_all()


if __name__ == "__main__":
    # 测试队列管理器
    import asyncio
    
    async def test_queues():
        # 测试音频队列
        audio_queue = get_audio_queue()
        await audio_queue.put(b"test audio data")
        data = await audio_queue.get()
        print(f"Audio queue test: {data}")
        
        # 测试文本队列
        text_queue = get_text_queue()
        await text_queue.put("测试文本")
        text = await text_queue.get()
        print(f"Text queue test: {text}")
        
        # 测试 LLM 队列
        llm_queue = get_llm_queue()
        await llm_queue.put("Hello")
        await llm_queue.put(" world")
        token1 = await llm_queue.get()
        token2 = await llm_queue.get()
        print(f"LLM queue test: {token1}{token2}")
        
        # 测试 TTS 队列
        tts_queue = get_tts_queue()
        await tts_queue.put(b"test tts audio")
        audio = await tts_queue.get()
        print(f"TTS queue test: {audio}")
        
        print("All queue tests passed!")
    
    asyncio.run(test_queues())
