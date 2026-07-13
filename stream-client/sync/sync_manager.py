"""Bridge between the WebSocket transport and the local media controller."""

from __future__ import annotations

import collections
import logging

from PyQt6.QtCore import QObject, pyqtSignal

from config.settings import Settings
from player.media_controller import MediaController
from sync import protocol
from sync.protocol import MessageType, SyncMessage, new_msg_id
from sync.ws_client import WebSocketClient

logger = logging.getLogger(__name__)

# Transport actions that map onto local playback when received from a peer.
_TRANSPORT_TYPES = {
    MessageType.PLAY,
    MessageType.PAUSE,
    MessageType.STOP,
    MessageType.SEEK,
}


class SyncManager(QObject):
    """Wires a :class:`WebSocketClient` to a :class:`MediaController`.

    Owns the room name, client name, and an echo-suppression window: outbound
    messages record their ``msg_id`` so the server's broadcast of our own action
    is ignored when it comes back, preventing feedback loops.
    """

    connectionStateChanged = pyqtSignal(object)  # ConnectionState
    peerActionApplied = pyqtSignal(object)  # SyncMessage
    errorOccurred = pyqtSignal(str)

    def __init__(
        self,
        controller: MediaController,
        settings: Settings,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._settings = settings
        self._ws = WebSocketClient()
        self._room: str = ""
        self._name: str = settings.client_name
        self._sent_ids: "collections.deque[str]" = collections.deque(maxlen=64)

        # Local transport actions -> broadcast to the room.
        self._controller.syncActionRequested.connect(self._on_local_action)
        # Inbound frames -> apply / surface.
        self._ws.messageReceived.connect(self._on_message)
        # On (re)connect, announce ourselves to the room.
        self._ws.connected.connect(self._on_ws_connected)
        # Forward connection lifecycle + errors to interested UI.
        self._ws.connectionStateChanged.connect(self.connectionStateChanged)
        self._ws.errorOccurred.connect(self.errorOccurred)

    # ------------------------------------------------------------------ public
    def connect(self, url: str, room: str, name: str) -> None:
        """Store the room/name identity and open the WebSocket connection."""
        self._room = room
        self._name = name
        logger.info("Sync connecting: url=%s room=%s name=%s", url, room, name)
        self._ws.connect_to(url)

    def disconnect(self) -> None:
        """Leave the room (best-effort) and close the connection."""
        if self._ws.is_connected() and self._room:
            leave = protocol.make(MessageType.LEAVE, room=self._room, sender=self._name)
            self._send(leave)
        self._ws.disconnect_from()

    def is_connected(self) -> bool:
        """Return ``True`` when the underlying socket is connected."""
        return self._ws.is_connected()

    # ----------------------------------------------------------------- private
    def _on_ws_connected(self) -> None:
        join = protocol.make(MessageType.JOIN, room=self._room, sender=self._name)
        self._send(join)

    def _on_local_action(self, msg: SyncMessage) -> None:
        """Stamp a locally originated action with our identity and broadcast it."""
        msg.room = self._room
        msg.sender = self._name
        if not msg.msg_id:
            msg.msg_id = new_msg_id()
        self._send(msg)

    def _send(self, msg: SyncMessage) -> None:
        self._sent_ids.append(msg.msg_id)
        logger.debug("Sending %s (id=%s)", msg.type.value, msg.msg_id)
        self._ws.send(msg.to_json())

    def _on_message(self, raw: str) -> None:
        try:
            msg = SyncMessage.from_json(raw)
        except (ValueError, TypeError) as exc:  # bad JSON or unknown type
            logger.warning("Dropping malformed sync message: %s (%s)", raw, exc)
            return

        # Suppress the echo of our own broadcast.
        if msg.msg_id and msg.msg_id in self._sent_ids:
            logger.debug("Ignoring echo of our own message id=%s", msg.msg_id)
            return

        # Ignore traffic for other rooms.
        if msg.room and self._room and msg.room != self._room:
            logger.debug("Ignoring message for other room %s", msg.room)
            return

        if msg.type in _TRANSPORT_TYPES:
            # apply_remote never re-broadcasts (broadcast=False internally).
            self._controller.apply_remote(msg)
            self.peerActionApplied.emit(msg)
        else:
            # JOIN / LEAVE / PEERS / PING / SYNC / ERROR -> surface for UI awareness.
            logger.info("Room event: %s from %s", msg.type.value, msg.sender)
            self.peerActionApplied.emit(msg)
