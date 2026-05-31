"""
统一日志配置模块 (基于 loguru)
"""

import sys
import os
from loguru import logger

def setup_logger(log_level: str = "INFO", log_file: str = "./logs/video_optimizer.log"):
    """
    配置全局 logger

    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        log_file: 日志文件路径
    """
    # 移除默认 handler
    logger.remove()

    # 控制台输出
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        colorize=True,
    )

    # 文件输出
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    logger.add(
        log_file,
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
               "{name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention="7 days",
        encoding="utf-8",
    )

    return logger


def get_logger(name: str = __name__):
    """
    获取带有模块名称标识的 logger 实例

    Args:
        name: 模块名称，通常传入 __name__

    Returns:
        loguru.Logger: 配置好的 logger 实例
    """
    return logger.bind(name=name)


# 模块加载时自动配置（使用默认值，后续可通过 setup_logger 重新配置）
setup_logger()
