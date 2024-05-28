import reflex as rx
from loguru import logger

from .config import CONFIG
from .pages import students

logger.add(
    CONFIG.log_path, rotation=CONFIG.log_rotation, retention=CONFIG.log_retention
)

app = rx.App()
