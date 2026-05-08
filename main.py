"""
智能体语音对话系统 - 主入口
"""
import asyncio
import logging
import signal
import sys
import os
from datetime import datetime

# 创建日志目录
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# 生成带日期的日志文件名
log_date = datetime.now().strftime("%Y-%m-%d")
log_file = os.path.join(log_dir, f"voice_agent_{log_date}.log")

# 配置日志格式
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 配置根日志记录器
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        # 控制台输出
        logging.StreamHandler(),
        # 文件输出（按日期）
        logging.FileHandler(log_file, encoding="utf-8")
    ]
)

logger = logging.getLogger(__name__)
logger.info(f"日志文件: {log_file}")


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
