"""
Centralised logging configuration for Code Migration Agent.

Provides:
  - Console handler  (coloured in development)
  - Rotating file handler (backend/logs/app.log)
  - Error-only file handler (backend/logs/error.log)

Usage:
    from app.core.logger import get_logger
    logger = get_logger(__name__)
"""

import logging
import logging.handlers
import os
import sys
from typing import Optional


# ── ANSI colour codes (development console only) ──────────────────────────

_COLOURS = {
    "DEBUG":    "\033[36m",   # cyan
    "INFO":     "\033[32m",   # green
    "WARNING":  "\033[33m",   # yellow
    "ERROR":    "\033[31m",   # red
    "CRITICAL": "\033[35m",   # magenta
    "RESET":    "\033[0m",
}


class ColouredFormatter(logging.Formatter):
    """Formatter that adds ANSI colour codes to level names."""

    def format(self, record: logging.LogRecord) -> str:
        colour = _COLOURS.get(record.levelname, "")
        reset = _COLOURS["RESET"]
        record.levelname = f"{colour}{record.levelname:<8}{reset}"
        return super().format(record)


# ── Module-level state ────────────────────────────────────────────────────

_configured = False


def configure_logging(
    level: str = "INFO",
    log_dir: str = "./logs",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    is_production: bool = False,
) -> None:
    """
    Configure the root logger once at application startup.

    Args:
        level:          Log level string (DEBUG / INFO / WARNING / ERROR).
        log_dir:        Directory where log files will be written.
        max_bytes:      Max size of a single log file before rotation.
        backup_count:   Number of rotated backups to keep.
        is_production:  Disable colour output in production.
    """
    global _configured
    if _configured:
        return

    os.makedirs(log_dir, exist_ok=True)

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # ── Formatters ────────────────────────────────────────────────────
    _fmt = "%(asctime)s | %(levelname)-8s | %(name)s — %(message)s"
    _datefmt = "%Y-%m-%d %H:%M:%S"

    plain_fmt = logging.Formatter(fmt=_fmt, datefmt=_datefmt)
    colour_fmt = ColouredFormatter(fmt=_fmt, datefmt=_datefmt)

    # ── Console handler ───────────────────────────────────────────────
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(numeric_level)
    console.setFormatter(plain_fmt if is_production else colour_fmt)

    # ── App rotating file handler (all levels) ────────────────────────
    app_log_path = os.path.join(log_dir, "app.log")
    file_handler = logging.handlers.RotatingFileHandler(
        filename=app_log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(plain_fmt)

    # ── Error-only file handler ───────────────────────────────────────
    error_log_path = os.path.join(log_dir, "error.log")
    error_handler = logging.handlers.RotatingFileHandler(
        filename=error_log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(plain_fmt)

    # ── Root logger ───────────────────────────────────────────────────
    root = logging.getLogger()
    root.setLevel(numeric_level)
    # Remove any handlers added by basicConfig earlier
    root.handlers.clear()
    root.addHandler(console)
    root.addHandler(file_handler)
    root.addHandler(error_handler)

    _configured = True

    logging.getLogger(__name__).info(
        "Logging configured — level=%s  log_dir=%s", level, log_dir
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Return a named logger.  Call configure_logging() before using this.

    Args:
        name: Logger name, typically ``__name__``.

    Returns:
        A :class:`logging.Logger` instance.
    """
    return logging.getLogger(name)
