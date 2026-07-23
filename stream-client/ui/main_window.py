"""Main application window wiring the media controller, control bar and sync manager."""

from __future__ import annotations

import logging
import os

from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QEvent, QSize
from PyQt6.QtGui import (
    QAction,
    QActionGroup,
    QKeyEvent,
    QKeySequence,
    QShortcut,
    QShowEvent,
)
from PyQt6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QPushButton,
)

from config.constants import (
    APP_NAME,
    ASPECT_RATIOS,
    DEFAULT_VOLUME,
    MEDIA_FILE_FILTER,
    SEEK_STEP_MS,
    STYLESHEET_PATH,
    VOLUME_STEP,
)
from config.settings import Settings
from core.enums import ConnectionState, PlayerState
from player.media_controller import MediaController
from sync.sync_manager import SyncManager
from ui.about_dialog import AboutDialog
from ui.branding import build_app_icon
from ui.connect_dialog import ConnectDialog
from ui import icons
from ui.control_bar import ControlBar
from ui.video_widget import VideoWidget
from utils.formatting import ms_to_hhmmss

logger = logging.getLogger(__name__)


_CONNECTION_LABELS: dict[ConnectionState, str] = {
    ConnectionState.DISCONNECTED: "Disconnected",
    ConnectionState.CONNECTING: "Connecting...",
    ConnectionState.CONNECTED: "Connected",
    ConnectionState.RECONNECTING: "Reconnecting...",
    ConnectionState.ERROR: "Connection error",
}


class MainWindow(QMainWindow):
    """Top-level window hosting the video surface, transport controls and menus."""

    def __init__(
        self,
        controller: MediaController,
        sync_manager: SyncManager,
        settings: Settings,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._sync = sync_manager
        self._settings = settings

        self._fullscreen = False
        self._window_attached = False
        self._volume = DEFAULT_VOLUME

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(build_app_icon())

        # Central widget: video surface (stretch) above the control bar.
        self._video = VideoWidget()
        self._control = ControlBar()

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._video, 1)
        layout.addWidget(self._control, 0)
        self.setCentralWidget(central)

        # Status bar with a persistent connection-state indicator.
        self._conn_label = QLabel("Sync: Disconnected")
        self._conn_label.setObjectName("connLabel")
        
        self._icon_hide = icons.chevron_down_icon("#C9CDD4")
        self._icon_show = icons.chevron_up_icon("#C9CDD4")
        
        self._toggle_btn = QPushButton()
        self._toggle_btn.setIcon(self._icon_hide)
        self._toggle_btn.setIconSize(QSize(20, 20))
        self._toggle_btn.setObjectName("toggleBtn")
        self._toggle_btn.setFixedSize(24, 24)
        self._toggle_btn.setToolTip("Hide Controls")
        self._toggle_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setStyleSheet("QPushButton { border: none; background: transparent; }")
        self._toggle_btn.clicked.connect(self.toggle_controls)
        
        self.statusBar().addPermanentWidget(self._toggle_btn)
        self.statusBar().addPermanentWidget(self._conn_label)

        self._build_menus()
        self._wire_signals()
        self._setup_shortcuts()
        self._apply_stylesheet()

        # Apply the default volume on startup.
        self._controller.set_volume(DEFAULT_VOLUME)
        self._control.set_volume(DEFAULT_VOLUME)

        self._controls_hidden = False
        self._animation = QPropertyAnimation(self._control, b"maximumHeight")
        self._animation.setDuration(300)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        logger.info("MainWindow constructed")

    # ------------------------------------------------------------------ setup

    def _build_menus(self) -> None:
        """Create the menu bar (File / Playback / Audio / Video / Subtitles / Sync)."""
        menubar = self.menuBar()

        # --- File -------------------------------------------------------
        file_menu = menubar.addMenu("&File")
        open_action = QAction("&Open File...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_file_dialog)
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # --- Playback ---------------------------------------------------
        playback_menu = menubar.addMenu("&Playback")
        play_action = QAction("Play / Pause", self)
        play_action.triggered.connect(lambda: self._controller.toggle_play_pause())
        playback_menu.addAction(play_action)
        stop_action = QAction("Stop", self)
        stop_action.triggered.connect(lambda: self._controller.stop())
        playback_menu.addAction(stop_action)
        playback_menu.addSeparator()
        forward_action = QAction("Step Forward", self)
        forward_action.triggered.connect(
            lambda: self._controller.seek_relative(SEEK_STEP_MS)
        )
        playback_menu.addAction(forward_action)
        back_action = QAction("Step Backward", self)
        back_action.triggered.connect(
            lambda: self._controller.seek_relative(-SEEK_STEP_MS)
        )
        playback_menu.addAction(back_action)

        # --- Audio (populated lazily) ----------------------------------
        self._audio_menu = menubar.addMenu("&Audio")
        self._audio_menu.aboutToShow.connect(self._populate_audio_menu)

        # --- Video ------------------------------------------------------
        video_menu = menubar.addMenu("&Video")
        fullscreen_action = QAction("Toggle Fullscreen", self)
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        video_menu.addAction(fullscreen_action)
        self._aspect_menu = video_menu.addMenu("Aspect Ratio")
        self._aspect_menu.aboutToShow.connect(self._populate_aspect_menu)

        # --- Subtitles (populated lazily) ------------------------------
        self._subtitle_menu = menubar.addMenu("&Subtitles")
        self._subtitle_menu.aboutToShow.connect(self._populate_subtitle_menu)

        # --- Sync -------------------------------------------------------
        sync_menu = menubar.addMenu("S&ync")
        connect_action = QAction("Connect...", self)
        connect_action.triggered.connect(self.show_connect_dialog)
        sync_menu.addAction(connect_action)
        disconnect_action = QAction("Disconnect", self)
        disconnect_action.triggered.connect(self.disconnect_sync)
        sync_menu.addAction(disconnect_action)

        # --- Help -------------------------------------------------------
        help_menu = menubar.addMenu("&Help")
        about_action = QAction(f"About {APP_NAME}", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def _wire_signals(self) -> None:
        """Connect control bar, controller and sync manager signals together."""
        # Control bar intents -> controller methods.
        self._control.playPauseClicked.connect(self._controller.toggle_play_pause)
        self._control.stopClicked.connect(self._controller.stop)
        self._control.seekRequested.connect(self._controller.seek)
        self._control.volumeChanged.connect(self._controller.set_volume)
        self._control.muteToggled.connect(self._controller.toggle_mute)
        self._control.rateChanged.connect(self._controller.set_rate)
        self._control.fullscreenToggled.connect(self.toggle_fullscreen)
        self._control.openFileClicked.connect(self.open_file_dialog)

        # Controller state -> control bar setters.
        self._controller.positionChanged.connect(self._control.set_position)
        self._controller.durationChanged.connect(self._control.set_duration)
        self._controller.stateChanged.connect(self._on_state)
        self._controller.volumeChanged.connect(self._control.set_volume)
        self._controller.volumeChanged.connect(self._on_volume_changed)
        self._controller.muteChanged.connect(self._control.set_muted)
        self._controller.rateChanged.connect(self._control.set_rate)
        self._controller.errorOccurred.connect(self._on_error)
        self._controller.mediaLoaded.connect(self._on_media_loaded)

        # Video surface double-click -> fullscreen toggle.
        self._video.doubleClicked.connect(self.toggle_fullscreen)

        # Sync manager -> status feedback.
        self._sync.connectionStateChanged.connect(self._on_connection)
        self._sync.peerActionApplied.connect(self._on_peer_action)
        self._sync.errorOccurred.connect(self._on_error)

    def _setup_shortcuts(self) -> None:
        """Install keyboard shortcuts for transport, seeking and volume."""

        def add(key, slot) -> QShortcut:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
            shortcut.activated.connect(slot)
            return shortcut

        add(Qt.Key.Key_Space, self._controller.toggle_play_pause)
        add(Qt.Key.Key_F, self.toggle_fullscreen)
        add(Qt.Key.Key_Escape, self._exit_fullscreen)
        add(Qt.Key.Key_Left, lambda: self._controller.seek_relative(-SEEK_STEP_MS))
        add(Qt.Key.Key_Right, lambda: self._controller.seek_relative(SEEK_STEP_MS))
        add(Qt.Key.Key_Up, lambda: self._change_volume(VOLUME_STEP))
        add(Qt.Key.Key_Down, lambda: self._change_volume(-VOLUME_STEP))
        add(Qt.Key.Key_M, self._controller.toggle_mute)
        add(Qt.Key.Key_O, self.open_file_dialog)

    def _apply_stylesheet(self) -> None:
        """Best-effort load of the dark stylesheet."""
        try:
            if os.path.isfile(STYLESHEET_PATH):
                with open(STYLESHEET_PATH, "r", encoding="utf-8") as handle:
                    self.setStyleSheet(handle.read())
                logger.debug("Applied stylesheet from %s", STYLESHEET_PATH)
        except OSError as exc:  # pragma: no cover - cosmetic only
            logger.warning("Could not load stylesheet %s: %s", STYLESHEET_PATH, exc)

    # ------------------------------------------------------------------ events

    def showEvent(self, e: QShowEvent) -> None:
        """Attach the native VLC surface once the window (and winId) is realised."""
        super().showEvent(e)
        if not self._window_attached:
            self._window_attached = True
            handle = self._video.window_handle()
            logger.info("Attaching VLC output to window handle %s", handle)
            self._controller.attach_window(handle)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        """Fallback key handling so arrows/space work even without shortcut focus."""
        key = event.key()
        if key == Qt.Key.Key_Space:
            self._controller.toggle_play_pause()
        elif key == Qt.Key.Key_Escape:
            self._exit_fullscreen()
        else:
            super().keyPressEvent(event)
            return
        event.accept()

    # ------------------------------------------------------------------ menus

    def _populate_audio_menu(self) -> None:
        """Rebuild the Audio menu with the currently available audio tracks."""
        self._audio_menu.clear()
        tracks = self._controller.audio_tracks()
        if not tracks:
            placeholder = self._audio_menu.addAction("No audio tracks")
            placeholder.setEnabled(False)
            return
        group = QActionGroup(self._audio_menu)
        group.setExclusive(True)
        for track in tracks:
            label = track.name or f"Track {track.id}"
            action = self._audio_menu.addAction(label)
            action.setCheckable(True)
            group.addAction(action)
            action.triggered.connect(
                lambda _checked=False, tid=track.id: self._controller.set_audio_track(tid)
            )

    def _populate_subtitle_menu(self) -> None:
        """Rebuild the Subtitles menu with the currently available SPU tracks."""
        self._subtitle_menu.clear()
        group = QActionGroup(self._subtitle_menu)
        group.setExclusive(True)

        disable_action = self._subtitle_menu.addAction("Disable")
        disable_action.setCheckable(True)
        group.addAction(disable_action)
        disable_action.triggered.connect(
            lambda _checked=False: self._controller.set_subtitle_track(-1)
        )

        tracks = self._controller.subtitle_tracks()
        if not tracks:
            return
        self._subtitle_menu.addSeparator()
        for track in tracks:
            label = track.name or f"Track {track.id}"
            action = self._subtitle_menu.addAction(label)
            action.setCheckable(True)
            group.addAction(action)
            action.triggered.connect(
                lambda _checked=False, sid=track.id: self._controller.set_subtitle_track(sid)
            )

    def _populate_aspect_menu(self) -> None:
        """Rebuild the Aspect Ratio submenu from the ASPECT_RATIOS mapping."""
        self._aspect_menu.clear()
        group = QActionGroup(self._aspect_menu)
        group.setExclusive(True)
        for label, ratio in ASPECT_RATIOS.items():
            action = self._aspect_menu.addAction(label)
            action.setCheckable(True)
            group.addAction(action)
            action.triggered.connect(
                lambda _checked=False, r=ratio: self._controller.set_aspect_ratio(r)
            )

    # ------------------------------------------------------------------ slots

    def _on_state(self, state: PlayerState) -> None:
        """Reflect the controller playback state in the UI."""
        self._control.set_playing(state == PlayerState.PLAYING)
        self.statusBar().showMessage(f"State: {state.name}", 2000)

    def _on_volume_changed(self, volume: int) -> None:
        """Track the current volume for relative keyboard adjustments."""
        self._volume = volume

    def _on_error(self, message: str) -> None:
        """Surface a controller/sync error via the status bar."""
        logger.error("Error reported to UI: %s", message)
        self.statusBar().showMessage(f"Error: {message}", 5000)

    def _on_media_loaded(self, info) -> None:
        """Update the window title when a new media item is loaded."""
        title = getattr(info, "title", "") or ""
        self.setWindowTitle(f"{APP_NAME} - {title}" if title else APP_NAME)

    def _on_connection(self, state: ConnectionState) -> None:
        """Update the persistent connection indicator in the status bar."""
        text = _CONNECTION_LABELS.get(state, str(state))
        self._conn_label.setText(f"Sync: {text}")
        logger.debug("Connection state -> %s", text)

    def _on_peer_action(self, msg) -> None:
        """Show a transient status message describing a peer's action."""
        sender = getattr(msg, "sender", "") or "peer"
        msg_type = getattr(msg, "type", None)
        type_text = getattr(msg_type, "value", str(msg_type))
        position = getattr(msg, "position_ms", 0)
        self.statusBar().showMessage(
            f"{sender}: {type_text} @ {ms_to_hhmmss(position)}", 3000
        )

    # ------------------------------------------------------------------ actions

    def open_file_dialog(self) -> None:
        """Prompt for a media file and hand it to the controller."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Media", "", MEDIA_FILE_FILTER
        )
        if not path:
            return
        logger.info("Opening media file: %s", path)
        self._controller.open_file(path)
        # Re-apply the current volume so it survives a fresh media load.
        self._controller.set_volume(self._volume)

    def toggle_fullscreen(self) -> None:
        """Toggle fullscreen presentation, hiding the menu bar while active."""
        if self._fullscreen:
            self.showNormal()
            self.menuBar().show()
            self._fullscreen = False
        else:
            self.showFullScreen()
            self.menuBar().hide()
            self._fullscreen = True
        logger.debug("Fullscreen -> %s", self._fullscreen)

    def toggle_controls(self) -> None:
        """Manually toggle the control bar visibility using animation."""
        if not self._controls_hidden:
            # Cache the current height before we shrink it to 0
            self._control_height = self._control.height()
            self._animation.stop()
            self._animation.setStartValue(self._control_height)
            self._animation.setEndValue(0)
            self._animation.start()
            self._controls_hidden = True
            self._toggle_btn.setIcon(self._icon_show)
            self._toggle_btn.setToolTip("Show Controls")
        else:
            self._animation.stop()
            self._animation.setStartValue(self._control.height())
            # Use the cached height or a fallback of 54
            target_h = getattr(self, "_control_height", 54)
            self._animation.setEndValue(target_h if target_h > 0 else 54)
            self._animation.start()
            self._controls_hidden = False
            self._toggle_btn.setIcon(self._icon_hide)
            self._toggle_btn.setToolTip("Hide Controls")

    def _exit_fullscreen(self) -> None:
        """Leave fullscreen mode if currently active (Esc handler)."""
        if self._fullscreen:
            self.toggle_fullscreen()

    def _change_volume(self, delta: int) -> None:
        """Adjust the volume by delta, clamped to the 0..100 range."""
        new_volume = max(0, min(100, self._volume + delta))
        self._controller.set_volume(new_volume)

    def show_connect_dialog(self) -> None:
        """Open the connect dialog and start a sync session with the chosen values."""
        dialog = ConnectDialog(self._settings, self)
        if dialog.exec():
            url, room, name = dialog.values()
            if not url:
                logger.warning("Connect cancelled: empty server URL")
                return
            logger.info("Connecting to %s (room=%s, name=%s)", url, room, name)
            self._sync.connect(url, room, name)

    def disconnect_sync(self) -> None:
        """Tear down the active sync session, if any."""
        logger.info("Disconnecting sync session")
        self._sync.disconnect()

    def show_about_dialog(self) -> None:
        """Show the branded About dialog."""
        AboutDialog(self).exec()
