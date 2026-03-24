"""
logger.py — Structured logging with Rich console output and file persistence.
"""

from __future__ import annotations
import logging
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme


LOGS_DIR = Path.home() / ".deploybot" / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

_theme = Theme({
    "logging.level.info":    "bold cyan",
    "logging.level.warning": "bold yellow",
    "logging.level.error":   "bold red",
    "logging.level.debug":   "dim",
})

console = Console(theme=_theme)


def get_logger(name: str = "deploybot") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Rich console handler
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        markup=True,
    )
    rich_handler.setLevel(logging.INFO)
    logger.addHandler(rich_handler)

    # File handler (full debug log)
    log_file = LOGS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s — %(message)s")
    )
    logger.addHandler(file_handler)

    return logger


log = get_logger()
