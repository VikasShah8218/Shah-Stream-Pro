"""Runtime branding helpers — load the application icon.

Loads the provided .ico file directly as a QIcon, which will be used
for both the taskbar and the title bar of the application.
"""

from __future__ import annotations

from PyQt6.QtGui import QIcon

from config.constants import ICON_PATH


def build_app_icon(*args, **kwargs) -> QIcon:
    """Return the application icon loaded from the .ico file."""
    return QIcon(ICON_PATH)
