#!/usr/bin/env python3
"""Shah-Stream sync server — a production-grade, single-file FastAPI WebSocket relay.

Room-based "watch together" relay for the Shah-Stream client. Every message a
client sends is relayed VERBATIM (``msg_id`` and ``room`` preserved) to all
clients in the SAME room — including the sender, whose own client drops the echo
by ``msg_id``. That round-trip is what keeps peers in sync.

Protocol (JSON text frames)::

    {"type": "join|play|pause|stop|seek|leave|...",
     "room": "<room-id>", "sender": "<name>",
     "position_ms": <int>, "rate": <float>,
     "msg_id": "<uuid-hex>", "timestamp": <float>, "extra": {}}

Endpoints:
    WebSocket  /        and  /ws     -> the sync relay (client connects to "/")
    GET        /health              -> liveness/readiness probe (used by Docker)
    GET        /stats               -> current rooms and peer counts
    GET        /                    -> service info (HTTP; WS shares the same path)

Configuration is intentionally fixed (no env vars, no .env): the server always
binds 0.0.0.0:8765. State is in-memory, so run exactly ONE process/worker;
horizontal scaling would require a shared broker (e.g. Redis pub/sub).

Run locally:
    pip install "fastapi" "uvicorn[standard]"
    python server.py
    # or, the ASGI way:  uvicorn server:app --host 0.0.0.0 --port 8765 --no-access-log
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# --------------------------------------------------------------------------- #
# Fixed configuration (no environment variables by design).
# --------------------------------------------------------------------------- #
HOST = "0.0.0.0"
PORT = 8765

#: Actions that move local playback on the receiving client (for log clarity only;
#: every message type is relayed regardless).
TRANSPORT_TYPES = {"play", "pause", "stop", "seek"}

#: Per-connection guard rails — a media-sync stream is low volume, so these are
#: generous ceilings that only trip on a buggy or abusive client.
MAX_MESSAGE_BYTES = 64 * 1024      # drop absurdly large frames
MAX_MESSAGES_PER_SEC = 50          # drop floods (per connection)
SEND_TIMEOUT_S = 5.0               # never let one slow peer stall a broadcast

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("shah-stream.sync")


def _fmt_ms(ms) -> str:
    """Format a millisecond position as H:MM:SS / MM:SS for readable logs."""
    try:
        ms = max(0, int(ms))
    except (TypeError, ValueError):
        return "?"
    h, rem = divmod(ms // 1000, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


# --------------------------------------------------------------------------- #
# Connection / room management.
# --------------------------------------------------------------------------- #
class ConnectionManager:
    """Tracks room membership and relays messages, guarding shared state with a lock.

    asyncio is single-threaded, but broadcasts ``await`` mid-iteration, so a lock
    plus snapshot-before-send keeps membership mutations from racing teardown.
    """

    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = {}
        self._meta: dict[WebSocket, tuple[str, str]] = {}  # ws -> (room, name)
        self._lock = asyncio.Lock()

    @property
    def room_count(self) -> int:
        return len(self._rooms)

    @property
    def connection_count(self) -> int:
        return len(self._meta)

    def snapshot(self) -> dict[str, int]:
        """Return a ``{room: peer_count}`` snapshot (read-only, lock-free)."""
        return {room: len(peers) for room, peers in self._rooms.items()}

    async def join(self, websocket: WebSocket, room: str, name: str) -> int:
        """Add/move a connection into ``room``; returns the room's new size."""
        async with self._lock:
            prev = self._meta.get(websocket)
            if prev and prev[0] != room:
                self._detach_locked(websocket, prev[0])
            self._rooms.setdefault(room, set()).add(websocket)
            self._meta[websocket] = (room, name)
            return len(self._rooms[room])

    async def leave(self, websocket: WebSocket) -> tuple[str, str] | None:
        """Remove a connection from its room; returns its ``(room, name)`` if known."""
        async with self._lock:
            meta = self._meta.pop(websocket, None)
            if meta:
                self._detach_locked(websocket, meta[0])
            return meta

    def _detach_locked(self, websocket: WebSocket, room: str) -> None:
        peers = self._rooms.get(room)
        if peers is not None:
            peers.discard(websocket)
            if not peers:
                self._rooms.pop(room, None)

    async def members(self, room: str) -> list[WebSocket]:
        async with self._lock:
            return list(self._rooms.get(room, ()))

    async def broadcast(self, room: str, raw: str) -> int:
        """Relay ``raw`` verbatim to every peer in ``room``. Returns delivered count.

        Sends run concurrently with a per-peer timeout; any peer that errors or
        stalls is pruned so it can't wedge future broadcasts.
        """
        targets = await self.members(room)
        if not targets:
            return 0

        dead: list[WebSocket] = []

        async def _send(ws: WebSocket) -> bool:
            try:
                await asyncio.wait_for(ws.send_text(raw), timeout=SEND_TIMEOUT_S)
                return True
            except Exception as exc:  # noqa: BLE001 - isolate one bad peer
                logger.debug("prune peer in room=%s (send failed: %s)", room, exc)
                dead.append(ws)
                return False

        results = await asyncio.gather(*(_send(ws) for ws in targets))

        for ws in dead:
            await self.leave(ws)
            try:
                await ws.close()
            except Exception:  # noqa: BLE001
                pass

        return sum(1 for ok in results if ok)


manager = ConnectionManager()


# --------------------------------------------------------------------------- #
# Application.
# --------------------------------------------------------------------------- #
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Shah-Stream sync server starting on ws://%s:%d", HOST, PORT)
    logger.info("Relay ready — clients join a room, then any peer's action syncs the rest.")
    try:
        yield
    finally:
        logger.info(
            "Shutting down (%d room(s), %d connection(s) open)",
            manager.room_count, manager.connection_count,
        )


app = FastAPI(
    title="Shah-Stream Sync Server",
    version="1.0.0",
    summary="Room-based WebSocket relay that keeps Shah-Stream clients in sync.",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict:
    """Liveness/readiness probe (used by the Docker healthcheck)."""
    return {
        "status": "ok",
        "rooms": manager.room_count,
        "connections": manager.connection_count,
    }


@app.get("/stats")
async def stats() -> dict:
    """Current rooms and their peer counts."""
    return {
        "rooms": manager.snapshot(),
        "room_count": manager.room_count,
        "total_connections": manager.connection_count,
    }


@app.get("/")
async def index() -> dict:
    """Human-friendly service info (HTTP GET; the WebSocket shares this path)."""
    return {
        "service": "shah-stream-sync-server",
        "version": "1.0.0",
        "status": "running",
        "websocket": ["/", "/ws"],
        "http": ["/health", "/stats"],
        "protocol": "JSON frames relayed verbatim to peers in the same room "
                    "(msg_id/room preserved); synced types: play, pause, stop, seek.",
        "stats": manager.snapshot(),
    }


async def _relay_connection(websocket: WebSocket) -> None:
    """Accept one client and relay its messages to its room until it disconnects."""
    await websocket.accept()
    client = websocket.client
    peer = f"{client.host}:{client.port}" if client else "?"
    room: str | None = None
    name = "?"
    logger.info("+ connect     %s", peer)

    # Simple per-connection flood guard (fixed 1-second window).
    loop = asyncio.get_running_loop()
    window_start = loop.time()
    window_count = 0

    try:
        while True:
            raw = await websocket.receive_text()

            # -- guard rails ------------------------------------------------
            if raw is None:
                continue
            if len(raw) > MAX_MESSAGE_BYTES:
                logger.warning("drop oversized frame (%d bytes) from %s", len(raw), peer)
                continue

            now = loop.time()
            if now - window_start >= 1.0:
                window_start = now
                window_count = 0
            window_count += 1
            if window_count > MAX_MESSAGES_PER_SEC:
                logger.warning("rate limit: dropping frame from %s (%s)", peer, name)
                continue

            # -- parse ------------------------------------------------------
            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                logger.warning("drop non-JSON frame from %s: %r", peer, raw[:120])
                continue
            if not isinstance(data, dict):
                logger.warning("drop non-object frame from %s", peer)
                continue

            mtype = str(data.get("type", "")).lower()
            target_room = str(data.get("room") or room or "lobby")
            name = str(data.get("sender") or name)

            # -- (re)register into the room --------------------------------
            if target_room != room:
                size = await manager.join(websocket, target_room, name)
                room = target_room
                if mtype != "join":
                    logger.debug("auto-registered %s into room=%s (%d in room)", peer, room, size)

            # -- relay verbatim (sender included; client drops its own echo)
            count = await manager.broadcast(room, raw)

            # -- log --------------------------------------------------------
            if mtype in TRANSPORT_TYPES:
                logger.info(
                    "  %-5s room=%-12s by=%-10s pos=%-8s -> %d peer(s)",
                    mtype.upper(), room, name, _fmt_ms(data.get("position_ms", 0)), count,
                )
            elif mtype == "join":
                logger.info("  JOIN  room=%-12s by=%-10s (%d in room)",
                            room, name, len(await manager.members(room)))
            elif mtype == "leave":
                logger.info("  LEAVE room=%-12s by=%-10s", room, name)
            else:
                logger.info("  %-5s room=%-12s by=%-10s -> %d peer(s)",
                            (mtype or "?").upper(), room, name, count)

    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001 - one client must never crash the server
        logger.exception("relay error for %s", peer)
    finally:
        meta = await manager.leave(websocket)
        left_room = meta[0] if meta else room
        remaining = len(await manager.members(left_room)) if left_room else 0
        logger.info("- disconnect  %s (room=%s, %d left)", peer, left_room, remaining)


@app.websocket("/")
async def websocket_root(websocket: WebSocket) -> None:
    await _relay_connection(websocket)


@app.websocket("/ws")
async def websocket_ws(websocket: WebSocket) -> None:
    await _relay_connection(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        access_log=False,          # relay events are logged above; skip HTTP access noise
        ws_ping_interval=20.0,     # keepalive: detect half-open peers
        ws_ping_timeout=20.0,
        timeout_graceful_shutdown=5,
    )
