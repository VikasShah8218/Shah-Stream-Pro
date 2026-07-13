"""Runtime settings loaded from environment variables and an optional .env file."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Tokens that parse to a boolean True value (case-insensitive).
_TRUE_VALUES: frozenset[str] = frozenset({"true", "1", "yes", "on"})


def _parse_bool(value: str) -> bool:
    """Parse a truthy string token (true/1/yes/on -> True) case-insensitively."""
    return value.strip().lower() in _TRUE_VALUES


@dataclass
class Settings:
    """User-configurable runtime settings for the application."""

    server_url: str
    default_room: str
    client_name: str
    auto_connect: bool
    log_level: str
    log_to_file: bool


def load_settings(env_path: str | None = None) -> Settings:
    """Load settings from environment variables, optionally seeding from a .env file.

    If ``env_path`` is given, that file is loaded. Otherwise the project-root
    ``.env`` is loaded when present; a missing file is not an error.
    """
    if env_path is not None:
        load_dotenv(env_path)
    else:
        # settings.py -> config -> stream-client -> <project root>
        root_env = Path(__file__).resolve().parents[2] / ".env"
        load_dotenv(root_env if root_env.exists() else None)

    settings = Settings(
        server_url=os.getenv("SHAH_SERVER_URL", "ws://localhost:8765"),
        default_room=os.getenv("SHAH_DEFAULT_ROOM", "lobby"),
        client_name=os.getenv("SHAH_CLIENT_NAME", "guest"),
        auto_connect=_parse_bool(os.getenv("SHAH_AUTO_CONNECT", "false")),
        log_level=os.getenv("SHAH_LOG_LEVEL", "INFO"),
        log_to_file=_parse_bool(os.getenv("SHAH_LOG_TO_FILE", "true")),
    )
    logger.debug("Loaded settings: %s", settings)
    return settings
