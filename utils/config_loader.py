"""
配置加载模块
"""
import yaml
from pathlib import Path
from typing import Dict, Any


def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    加载配置文件
    
    Args:
        config_path: 配置文件路径，默认为项目根目录下的 config.yaml
        
    Returns:
        配置字典
    """
    if config_path is None:
        # 默认配置文件路径
        config_path = Path(__file__).parent.parent / "config.yaml"
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    return config


def get_gateway_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取网关层配置"""
    return config.get("gateway", {})


def get_auditory_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取听觉层配置"""
    return config.get("auditory", {})


def get_cognition_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取认知层配置"""
    return config.get("cognition", {})


def get_tts_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取发声层配置"""
    return config.get("tts", {})


if __name__ == "__main__":
    # 测试配置加载
    config = load_config()
    print("网关层配置:", get_gateway_config(config))
    print("听觉层配置:", get_auditory_config(config))
    print("认知层配置:", get_cognition_config(config))
    print("发声层配置:", get_tts_config(config))
