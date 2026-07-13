"""Static application-wide constants for Shah-Stream."""
from __future__ import annotations

import os
import sys

# --- Application identity -------------------------------------------------
APP_NAME: str = "Shah-Stream"
APP_VERSION: str = "0.1.0"
ORG_NAME: str = "Shah"
APP_TAGLINE: str = "Play anything. Watch together."
APP_DESCRIPTION: str = (
    "A libVLC-powered media player with room-based watch-together sync."
)

# Windows AppUserModelID — makes the taskbar use the app's own icon and identity
# instead of the host python.exe. Set once, before any window is shown.
APP_ID: str = "Shah.ShahStream.Player.1"

# --- Asset paths ----------------------------------------------------------
def _resource_base() -> str:
    """Root of bundled resources.

    From source this is the project root dir ``stream-client/`` (constants.py lives
    two levels below it). Inside a PyInstaller one-file exe, data is unpacked to
    ``sys._MEIPASS``; the spec places our assets under ``stream-client/`` there, so
    both modes resolve to the same relative layout. (The image folder is spelled
    "assests" on disk.)
    """
    if getattr(sys, "frozen", False):
        return os.path.join(getattr(sys, "_MEIPASS", ""), "stream-client")
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


_PACKAGE_DIR: str = _resource_base()
ASSETS_DIR: str = os.path.join(_PACKAGE_DIR, "assests")
IMAGES_DIR: str = os.path.join(ASSETS_DIR, "img")
LOGO_PATH: str = os.path.join(IMAGES_DIR, "shah-logo.png")
ICON_PATH: str = os.path.join(IMAGES_DIR, "shah-logo.ico")
STYLESHEET_PATH: str = os.path.join(_PACKAGE_DIR, "ui", "styles", "dark.qss")

# --- Playback defaults ----------------------------------------------------
DEFAULT_VOLUME: int = 80
VOLUME_STEP: int = 5
SEEK_STEP_MS: int = 5000

DEFAULT_RATE: float = 1.0
PLAYBACK_RATES: list[float] = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0]

# --- Timers / intervals ---------------------------------------------------
POSITION_POLL_INTERVAL_MS: int = 250
RECONNECT_INTERVAL_MS: int = 3000

# --- Video aspect ratios (label -> libVLC aspect-ratio string) ------------
ASPECT_RATIOS: dict[str, str] = {
    "Default": "",
    "16:9": "16:9",
    "4:3": "4:3",
    "1:1": "1:1",
    "16:10": "16:10",
    "2.35:1": "235:100",
}

# --- Qt file-dialog filter for opening media ------------------------------
MEDIA_FILE_FILTER: str = (
    "Video Files (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm *.m4v "
    "*.mpg *.mpeg *.ts *.m2ts *.3gp *.ogv);;"
    "Audio Files (*.mp3 *.flac *.aac *.wav *.ogg *.m4a *.wma *.opus);;"
    "All Files (*)"
)
