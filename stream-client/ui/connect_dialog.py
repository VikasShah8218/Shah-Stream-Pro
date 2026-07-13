"""Modal dialog collecting the parameters needed to start a sync session."""

from __future__ import annotations

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from config.constants import LOGO_PATH
from config.settings import Settings

logger = logging.getLogger(__name__)


class ConnectDialog(QDialog):
    """Prompt the user for the server URL, room and display name to join."""

    def __init__(self, settings: Settings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Watch Together")
        self.setModal(True)
        self.setMinimumWidth(400)
        self._settings = settings

        # --- Header: logo + title + subtitle --------------------------------
        logo = QLabel()
        logo.setObjectName("dialogLogo")
        logo.setFixedSize(48, 48)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(LOGO_PATH)
        if not pixmap.isNull():
            logo.setPixmap(
                pixmap.scaled(
                    36,
                    36,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

        title = QLabel("Join a room")
        title.setObjectName("dialogTitle")
        subtitle = QLabel("Sync playback with everyone in the same room.")
        subtitle.setObjectName("dialogSubtitle")
        subtitle.setWordWrap(True)

        heading = QVBoxLayout()
        heading.setSpacing(2)
        heading.addWidget(title)
        heading.addWidget(subtitle)

        header = QHBoxLayout()
        header.setSpacing(12)
        header.addWidget(logo)
        header.addLayout(heading, 1)

        # --- Form -----------------------------------------------------------
        self._url_edit = QLineEdit(settings.server_url)
        self._url_edit.setPlaceholderText("ws://host:port")
        self._room_edit = QLineEdit(settings.default_room)
        self._room_edit.setPlaceholderText("room name")
        self._name_edit = QLineEdit(settings.client_name)
        self._name_edit.setPlaceholderText("your display name")

        form = QFormLayout()
        form.setSpacing(10)
        form.setContentsMargins(0, 0, 0, 0)
        form.addRow("Server URL", self._url_edit)
        form.addRow("Room", self._room_edit)
        form.addRow("Name", self._name_edit)

        # --- Buttons --------------------------------------------------------
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Connect")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(16)
        layout.addLayout(header)
        layout.addLayout(form)
        layout.addWidget(buttons)

        logger.debug("ConnectDialog initialised with defaults from settings")

    def values(self) -> tuple[str, str, str]:
        """Return the (url, room, name) tuple with surrounding whitespace stripped."""
        return (
            self._url_edit.text().strip(),
            self._room_edit.text().strip(),
            self._name_edit.text().strip(),
        )
