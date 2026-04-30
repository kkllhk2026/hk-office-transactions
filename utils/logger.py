"""Project-wide logger using loguru. Files rotate daily."""
from __future__ import annotations

import sys
from loguru import logger
from config.settings import LOGS_DIR

logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
           "<level>{level:<8}</level> | "
           "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
           "<level>{message}</level>",
)
logger.add(
    LOGS_DIR / "app_{time:YYYY-MM-DD}.log",
    level="DEBUG",
    rotation="00:00",
    retention="30 days",
    compression="zip",
    encoding="utf-8",
)

__all__ = ["logger"]
