"""
FastAPI + WebSocket 服务器
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import logging
import uuid
import os

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

# 获取项目根目录和前端目录
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_dir = os.path.join(project_root, "frontend")
logger.info(f"前端目录: {frontend_dir}")


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
    audio_count = 0
    while True:
        try:
            # 接收音频数据 (Binary frame)
            audio_data = await websocket.receive_bytes()
            audio_count += 1
            
            # 记录接收到的音频数据
            logger.info(f"📥 收到音频数据 #{audio_count}: {len(audio_data)} 字节")
            
            # 放入音频队列
            await audio_queue.put(audio_data)
            logger.debug(f"✅ 音频数据已放入队列 (队列大小: {audio_queue.qsize()})")
            
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


# 挂载前端目录作为静态文件（放在最后，确保 API 路由优先匹配）
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


if __name__ == "__main__":
    start_server()
