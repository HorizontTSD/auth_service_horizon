# src/core/logger.py
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.core.configuration.config import settings


class LoggerManager:
    def __init__(self):
        self.LOG_DIR = Path("logs")
        self.LOG_DIR.mkdir(exist_ok=True)

        self.FORMAT = f"[%(asctime)s] [%(levelname)s] [{settings.SERVICE_NAME}] %(message)s"
        self.DATE_FMT = "%Y-%m-%d %H:%M:%S"

    def _add_console_handler(self, logger: logging.Logger, formatter: logging.Formatter) -> None:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    def _add_file_handler(
            self,
            logger: logging.Logger,
            formatter: logging.Formatter,
            handler_type: str,
            level: int,
            filter_func: callable
        ) -> None:
        try:
            handler = RotatingFileHandler(
                self.LOG_DIR / f"{settings.SERVICE_NAME}_{handler_type}.log",
                maxBytes=5 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            handler.setLevel(level)
            handler.setFormatter(formatter)
            handler.addFilter(filter_func)
            logger.addHandler(handler)
        except Exception as e:
            print(f"Failed to setup {handler_type} file handler: {e}")

    def setup_logger(self) -> logging.Logger:
        logger = logging.getLogger()
        
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter(fmt=self.FORMAT, datefmt=self.DATE_FMT)

        self._add_console_handler(logger, formatter)
        self._add_file_handler(logger, formatter, "info", logging.INFO, lambda r: r.levelno == logging.INFO)
        self._add_file_handler(logger, formatter, "debug", logging.DEBUG, lambda r: r.levelno <= logging.DEBUG)
        self._add_file_handler(logger, formatter, "error", logging.ERROR, lambda r: r.levelno >= logging.ERROR)

        return logger


logger_manager = LoggerManager()
logger = logger_manager.setup_logger()
logger.setLevel(settings.LOGGER_LEVEL)