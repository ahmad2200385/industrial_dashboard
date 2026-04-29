import logging
from logging.config import dictConfig
from pathlib import Path

from core.config import settings


def setup_logging() -> None:
    log_file = Path(settings.LOG_FILE)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    dictConfig(
        {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'default': {
                    'format': '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'default',
                },
                'file': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'filename': str(log_file),
                    'maxBytes': 5 * 1024 * 1024,
                    'backupCount': 3,
                    'formatter': 'default',
                },
            },
            'root': {
                'level': settings.LOG_LEVEL,
                'handlers': ['console', 'file'],
            },
        }
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
