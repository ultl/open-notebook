from __future__ import annotations

import os
import sys

from loguru import logger


def configure_logging() -> None:
  level = os.getenv('LOG_LEVEL', 'INFO')
  logger.remove()
  logger.add(
    sys.stdout,
    level=level,
    format='{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} - {message}',
    enqueue=True,
    backtrace=False,
    diagnose=False,
  )
