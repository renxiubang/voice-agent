"""
FastAPI + WebSocket 服务器
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import asyncio
import logging
import uuid

from gateway.connection_manager import manager
from core.queues import get_audio_queue, get_tts_queue
from utils.config_loader import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(title="智能体语音对话系统 - 网关层")

# 加载配置
config = load_config()
gateway_config = config["gateway"]


@app.get("/")
async def root():
    """根路径 - 返回前端页面"""
    from fastapi.responses import FileResponse
    
    import os
    frontend_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "frontend",
        "index.html"
    )
    
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    else:
        return HTMLResponse(content="<h1>智能体语音对话系统</h1><p>前端页面未找到</p>")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 端点
    接收前端音频流，发送 TTS 音频流
    """
    # 生成客户端 ID
    client_id = str(uuid.uuid4())
    
    # 接受连接
    await manager.connect(websocket, client_id)
    
    # 获取队列
    audio_queue = get_audio_queue()
    tts_queue = get_tts_queue()
    
    try:
        # 并行运行接收和发送任务（全双工）
        await asyncio.gather(
            receive_audio(websocket, audio_queue),
            send_tts_audio(websocket, tts_queue)
        )
    except WebSocketDisconnect:
        # 客户端断开连接
        manager.disconnect(client_id)
        logger.info(f"客户端 {client_id} 断开连接")
    except Exception as e:
        # 其他错误
        logger.error(f"WebSocket 错误: {e}")
        manager.disconnect(client_id)


async def receive_audio(websocket: WebSocket, audio_queue: asyncio.Queue):
    """
    接收前端音频流的任务
    
    Args:
        websocket: WebSocket 连接
        audio_queue: 音频队列
    """
    while True:
        try:
            # 接收音频数据 (Binary frame)
            audio_data = await websocket.receive_bytes()
            
            # 放入音频队列
            await audio_queue.put(audio_data)
            
        except Exception as e:
            logger.error(f"接收音频错误: {e}")
            break


async def send_tts_audio(websocket: WebSocket, tts_queue: asyncio.Queue):
    """
    发送 TTS 音频流的任务
    
    Args:
        websocket: WebSocket 连接
        tts_queue: TTS 音频队列
    """
    while True:
        try:
            # 从 TTS 队列取出音频数据
            audio_data = await tts_queue.get()
            
            # 发送到前端 (Binary frame)
            await websocket.send_bytes(audio_data)
            
        except Exception as e:
            logger.error(f"发送 TTS 音频错误: {e}")
            break


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


def start_server():
    """启动服务器"""
    import uvicorn
    
    host = gateway_config.get("host", "0.0.0.0")
    port = gateway_config.get("port", 8000)
    
    logger.info(f"启动网关层服务器: {host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_server()
