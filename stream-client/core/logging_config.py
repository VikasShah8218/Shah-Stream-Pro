"""Application logging configuration (console + optional rotating file handler)."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config.settings import Settings

logger = logging.getLogger(__name__)

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_MAX_BYTES = 1_000_000
_BACKUP_COUNT = 3


def configure_logging(settings: "Settings") -> None:
    """Configure the root logger from ``settings``.

    Idempotent: existing handlers are cleared first so repeated calls do not
    accumulate duplicate handlers. A console handler is always attached; when
    ``settings.log_to_file`` is true a rotating file handler writing to
    ``<project_root>/logs/log`` is added as well.
    """
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # Idempotent: drop any handlers from a previous configuration.
    for handler in list(root.handlers):
        root.removeHandler(handler)
        try:
            handler.close()
        except Exception:  # noqa: BLE001 - best-effort cleanup
            pass

    formatter = logging.Formatter(_LOG_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    if settings.log_to_file:
        # <project_root>/logs — this module lives at
        # <project_root>/stream-client/core/logging_config.py, so walk up
        # three levels: core -> stream-client -> project_root.
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        logs_dir = os.path.join(project_root, "logs")
        try:
            os.makedirs(logs_dir, exist_ok=True)
            file_path = os.path.join(logs_dir, "log")
            file_handler = RotatingFileHandler(
                file_path,
                maxBytes=_MAX_BYTES,
                backupCount=_BACKUP_COUNT,
                encoding="utf-8",
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
        except OSError:
            logger.exception("Failed to set up file logging in %s", logs_dir)

    logger.debug("Logging configured at level %s (file=%s)", settings.log_level, settings.log_to_file)
