"""
Structured Logging Module for CAGED Framework.
"""

import logging
import sys
from typing import Any, Dict


def setup_logging(log_level: str = "INFO") -> None:
    """Configures structured logging for stdout output."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Silence verbose third-party loggers if necessary
    logging.getLogger("uvicorn.access").setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """Returns a named logger instance."""
    return logging.getLogger(name)
