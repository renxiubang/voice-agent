"""
WebSocket 连接管理器
"""
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    WebSocket 连接管理器
    支持多客户端连接
    """
    
    def __init__(self):
        # 活跃连接字典: {client_id: WebSocket}
        self.active_connections: Dict[str, "WebSocket"] = {}
    
    async def connect(self, websocket: "WebSocket", client_id: str):
        """
        接受新连接
        
        Args:
            websocket: WebSocket 连接
            client_id: 客户端 ID
        """
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"客户端 {client_id} 已连接")
    
    def disconnect(self, client_id: str):
        """
        断开连接
        
        Args:
            client_id: 客户端 ID
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"客户端 {client_id} 已断开")
    
    async def send_audio(self, client_id: str, audio_data: bytes):
        """
        发送音频数据到指定客户端
        
        Args:
            client_id: 客户端 ID
            audio_data: 音频数据 (PCM bytes)
        """
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await websocket.send_bytes(audio_data)
    
    async def broadcast_audio(self, audio_data: bytes):
        """
        广播音频数据到所有连接的客户端
        
        Args:
            audio_data: 音频数据 (PCM bytes)
        """
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_bytes(audio_data)
            except Exception as e:
                logger.error(f"广播音频到客户端 {client_id} 失败: {e}")
    
    def get_connected_clients(self) -> List[str]:
        """
        获取所有连接的客户端 ID
        
        Returns:
            客户端 ID 列表
        """
        return list(self.active_connections.keys())
    
    def is_connected(self, client_id: str) -> bool:
        """
        检查客户端是否已连接
        
        Args:
            client_id: 客户端 ID
            
        Returns:
            是否已连接
        """
        return client_id in self.active_connections


# 全局连接管理器实例
manager = ConnectionManager()


if __name__ == "__main__":
    # 测试连接管理器
    import asyncio
    from fastapi import FastAPI, WebSocket
    
    app = FastAPI()
    manager = ConnectionManager()
    
    @app.websocket("/ws/{client_id}")
    async def websocket_endpoint(websocket: WebSocket, client_id: str):
        await manager.connect(websocket, client_id)
        
        try:
            while True:
                # 接收消息
                data = await websocket.receive_bytes()
                print(f"收到来自 {client_id} 的数据: {len(data)} bytes")
                
                # 回显数据
                await manager.send_audio(client_id, data)
        except Exception as e:
            print(f"连接错误: {e}")
        finally:
            manager.disconnect(client_id)
    
    # 启动服务器
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
