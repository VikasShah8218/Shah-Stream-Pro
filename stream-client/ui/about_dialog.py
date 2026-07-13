"""Branded 'About' dialog showing the Shah-Stream identity and version."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from config.constants import (
    APP_DESCRIPTION,
    APP_NAME,
    APP_TAGLINE,
    APP_VERSION,
    LOGO_PATH,
)


class AboutDialog(QDialog):
    """Small modal presenting the logo, name, tagline, version and description."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setModal(True)
        self.setFixedWidth(400)

        # Logo on a light rounded card so the black-and-white mark always reads,
        # regardless of whether the source PNG is transparent.
        logo = QLabel()
        logo.setObjectName("aboutLogo")
        logo.setFixedSize(120, 120)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(LOGO_PATH)
        if not pixmap.isNull():
            logo.setPixmap(
                pixmap.scaled(
                    92,
                    92,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

        title = QLabel(APP_NAME)
        title.setObjectName("aboutTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        tagline = QLabel(APP_TAGLINE)
        tagline.setObjectName("aboutTagline")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)

        version = QLabel(f"Version {APP_VERSION}")
        version.setObjectName("aboutMeta")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)

        description = QLabel(APP_DESCRIPTION)
        description.setObjectName("aboutMeta")
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)

        close_btn = QPushButton("Close")
        close_btn.setDefault(True)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(close_btn)
        button_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 22)
        layout.setSpacing(10)
        layout.addWidget(logo, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title)
        layout.addWidget(tagline)
        layout.addSpacing(4)
        layout.addWidget(version)
        layout.addWidget(description)
        layout.addSpacing(8)
        layout.addLayout(button_row)
