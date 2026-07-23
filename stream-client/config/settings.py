"""Runtime settings loaded from environment variables and an optional .env file."""
from __future__ import annotations

import logging
import sys
import json
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class Settings:
    """User-configurable runtime settings for the application."""

    server_url: str
    default_room: str
    client_name: str
    auto_connect: bool
    log_level: str
    log_to_file: bool


def load_settings(config_path: str | None = None) -> Settings:
    """Load settings from a JSON config file.

    If ``config_path`` is given, that file is loaded. Otherwise the project-root
    ``config.json`` is loaded. A missing file or missing keys will raise an error.
    """
    if config_path is None:
        if getattr(sys, "frozen", False):
            # Running as compiled PyInstaller executable
            base_dir = Path(sys.executable).parent
        else:
            # Running from source (settings.py -> config -> stream-client)
            base_dir = Path(__file__).resolve().parents[1]
        
        config_path = str(base_dir / "config.json")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file {config_path}: {e}")

    try:
        settings = Settings(
            server_url=data["server_url"],
            default_room=data["default_room"],
            client_name=data["client_name"],
            auto_connect=bool(data["auto_connect"]),
            log_level=data["log_level"],
            log_to_file=bool(data["log_to_file"]),
        )
    except KeyError as e:
        raise KeyError(f"Missing required configuration key in {config_path}: {e}")

    logger.debug("Loaded settings: %s", settings)
    return settings
