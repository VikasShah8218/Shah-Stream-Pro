"""Application bootstrap for the Shah-Stream synced media player."""

from __future__ import annotations

import logging
import sys

from PyQt6.QtWidgets import QApplication

from config.constants import APP_ID, APP_NAME, ORG_NAME, STYLESHEET_PATH
from config.settings import load_settings
from core.logging_config import configure_logging
from player.media_controller import MediaController
from sync.sync_manager import SyncManager
from ui.branding import build_app_icon
from ui.main_window import MainWindow

logger = logging.getLogger(__name__)


def _load_stylesheet() -> str:
    """Return the contents of the dark stylesheet, or "" if unavailable."""
    try:
        with open(STYLESHEET_PATH, "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        logger.debug("Stylesheet not applied (%s): %s", STYLESHEET_PATH, exc)
        return ""


def _set_windows_app_id() -> None:
    """Tell Windows this is its own app so the taskbar shows our icon, not python.exe's."""
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        except Exception:  # noqa: BLE001 - purely cosmetic; never fail startup
            logger.debug("Could not set AppUserModelID", exc_info=True)


def main() -> int:
    """Build the Qt application, wire the player and sync stack, and run it."""
    settings = load_settings()
    configure_logging(settings)
    logger.info("Starting %s", APP_NAME)

    _set_windows_app_id()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    app.setWindowIcon(build_app_icon())

    stylesheet = _load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)

    controller = MediaController()
    sync = SyncManager(controller, settings)

    window = MainWindow(controller, sync, settings)
    window.resize(960, 600)
    window.show()

    if settings.auto_connect and settings.default_room:
        logger.info(
            "Auto-connecting to %s room=%s as %s",
            settings.server_url,
            settings.default_room,
            settings.client_name,
        )
        sync.connect(settings.server_url, settings.default_room, settings.client_name)

    try:
        rc = app.exec()
    finally:
        controller.release()

    logger.info("%s exited with code %s", APP_NAME, rc)
    return rc


if __name__ == "__main__":
    sys.exit(main())
