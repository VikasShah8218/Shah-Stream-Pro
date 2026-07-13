"""Qt-native single-connection WebSocket client with automatic reconnect."""

from __future__ import annotations

import logging

from PyQt6.QtCore import QObject, QTimer, QUrl, pyqtSignal
from PyQt6.QtNetwork import QAbstractSocket
from PyQt6.QtWebSockets import QWebSocket

from config.constants import RECONNECT_INTERVAL_MS
from core.enums import ConnectionState

logger = logging.getLogger(__name__)


class WebSocketClient(QObject):
    """Thin wrapper around a single :class:`QWebSocket`.

    Runs entirely on the Qt event loop (no worker threads). Re-emits inbound
    text frames verbatim and, unless the user explicitly disconnected, tries to
    reconnect on unexpected drops.
    """

    connected = pyqtSignal()
    disconnected = pyqtSignal()
    connectionStateChanged = pyqtSignal(object)  # ConnectionState
    messageReceived = pyqtSignal(str)  # raw text
    errorOccurred = pyqtSignal(str)

    def __init__(
        self,
        reconnect: bool = True,
        reconnect_interval_ms: int = RECONNECT_INTERVAL_MS,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._ws = QWebSocket()
        self._ws.connected.connect(self._on_connected)
        self._ws.disconnected.connect(self._on_disconnected)
        self._ws.textMessageReceived.connect(self.messageReceived)  # re-emit verbatim
        self._ws.errorOccurred.connect(self._on_error)

        self._url: str = ""
        self._user_closed: bool = False
        self._reconnect: bool = reconnect
        self._reconnect_interval_ms: int = reconnect_interval_ms
        self._state: ConnectionState = ConnectionState.DISCONNECTED

        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setSingleShot(True)
        self._reconnect_timer.setInterval(reconnect_interval_ms)
        self._reconnect_timer.timeout.connect(self._on_reconnect_timeout)

    # ------------------------------------------------------------------ public
    def connect_to(self, url: str) -> None:
        """Open a connection to ``url`` (clears the user-closed flag)."""
        self._url = url
        self._user_closed = False
        self._set_state(ConnectionState.CONNECTING)
        logger.info("WebSocket connecting to %s", url)
        self._ws.open(QUrl(url))

    def send(self, text: str) -> bool:
        """Send a text frame. Returns ``True`` if it was handed to the socket."""
        if not self.is_connected():
            logger.warning("Cannot send while disconnected: %s", text)
            return False
        sent = self._ws.sendTextMessage(text)
        return sent > 0

    def disconnect_from(self) -> None:
        """Close the connection at the user's request (suppresses reconnect)."""
        self._user_closed = True
        self._reconnect_timer.stop()
        self._ws.close()
        self._set_state(ConnectionState.DISCONNECTED)

    def is_connected(self) -> bool:
        """Return ``True`` when the underlying socket is fully connected."""
        return self._ws.state() == QAbstractSocket.SocketState.ConnectedState

    # ----------------------------------------------------------------- private
    def _set_state(self, state: ConnectionState) -> None:
        self._state = state
        logger.debug("Connection state -> %s", state.name)
        self.connectionStateChanged.emit(state)

    def _on_connected(self) -> None:
        self._reconnect_timer.stop()
        self._set_state(ConnectionState.CONNECTED)
        logger.info("WebSocket connected to %s", self._url)
        self.connected.emit()

    def _on_disconnected(self) -> None:
        logger.info("WebSocket disconnected from %s", self._url)
        self.disconnected.emit()
        if not self._user_closed and self._reconnect and self._url:
            self._set_state(ConnectionState.RECONNECTING)
            self._reconnect_timer.start()
        else:
            self._set_state(ConnectionState.DISCONNECTED)

    def _on_reconnect_timeout(self) -> None:
        if self._user_closed or not self._url:
            return
        logger.info("Attempting reconnect to %s", self._url)
        self.connect_to(self._url)

    def _on_error(self, err) -> None:
        message = str(self._ws.errorString())
        logger.error("WebSocket error (%s): %s", err, message)
        self.errorOccurred.emit(message)
        self._set_state(ConnectionState.ERROR)
