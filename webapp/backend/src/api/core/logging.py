import logging
import sys
from typing import Optional

from .config import settings


def setup_logging(log_level: Optional[str] = None) -> None:
    """
    Configure logging with the specified log level from settings.

    Args:
        log_level: Optional override for the log level. If not provided,
                  the log_level from settings is used.
    """
    level = log_level or settings.log_level
    numeric_level = getattr(logging, level.upper(), None)

    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")

    # Configure the root logger
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Log a message to confirm setup
    logger = logging.getLogger(__name__)
    logger.debug(f"Logging configured with level: {level}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    Args:
        name: The name of the logger, typically __name__ of the calling module.

    Returns:
        A configured Logger instance.
    """
    return logging.getLogger(name)
