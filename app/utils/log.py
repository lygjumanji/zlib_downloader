# coding:utf-8
import sys
import os
from loguru import logger


def setup_logger():
    logger.remove()
    if sys.stderr is not None:
        logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}")
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    log_file = os.path.join(base_dir, 'app_debug.log')
    logger.add(log_file, rotation="1 MB", retention="10 days", compression="zip", level="DEBUG")
