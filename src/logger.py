#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志配置模块

使用 loguru 提供彩色日志输出，支持不同级别的日志显示。
"""

import sys
from loguru import logger
from pathlib import Path

# 移除默认的日志处理器
logger.remove()

# 添加控制台彩色日志处理器
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG",
    colorize=True,
    backtrace=True,
    diagnose=True
)

# 添加文件日志处理器（可选）
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logger.add(
    log_dir / "app_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="INFO",
    rotation="1 day",
    retention="7 days",
    compression="zip",
    encoding="utf-8"
)

# 导出配置好的logger
__all__ = ["logger"]