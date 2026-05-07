"""
智能体语音对话系统 - 主入口
"""
import asyncio
import logging
import signal
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def main():
    """主函数"""
    logger.info("正在启动智能体语音对话系统...")
    
    # 加载配置
    from utils.config_loader import load_config
    config = load_config()
    
    # 启动网关层服务器 (在单独的进程中)
    from multiprocessing import Process
    from gateway.server import start_server
    
    gateway_process = Process(target=start_server)
    gateway_process.start()
    logger.info(f"网关层已启动 (PID: {gateway_process.pid})")
    
    # 启动核心编排器
    from core.orchestrator import Orchestrator
    
    orchestrator = Orchestrator(config)
    
    try:
        # 启动编排器 (会初始化所有模块)
        await orchestrator.start()
    except KeyboardInterrupt:
        logger.info("收到停止信号...")
    except Exception as e:
        logger.error(f"系统错误: {e}")
    finally:
        # 停止编排器
        await orchestrator.stop()
        
        # 停止网关层
        gateway_process.terminate()
        gateway_process.join()
        logger.info("网关层已停止")
        
        logger.info("系统已停止")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("程序已退出")
        sys.exit(0)
