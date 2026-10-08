"""The preview socket client — the client side of ``pydrud dev``.

Owns one TCP connection and one daemon reader thread. It performs the
authenticated ``preview_hello`` / ``preview_welcome`` handshake, then speaks
the renderer-v2 bridge protocol: it applies revisioned render transactions to
the :class:`~app.preview.mirror.RemoteTree`, ACKs (or NACKs) each one, and
forwards every other server command to the renderer.

Everything that touches the UI is handed back through callbacks; the caller
(:mod:`app.preview.session`) marshals those onto the app's UI thread.
"""

from __future__ import annotations

import json
import socket
import threading
from typing import Any, Callable, Optional

from app.config import (
    CLIENT_CAPABILITIES,
    CLIENT_NAME,
    CLIENT_PLATFORM,
    CONNECT_TIMEOUT,
    HANDSHAKE_TIMEOUT,
    PREVIEW_PROTOCOL,
    PREVIEW_PROTOCOL_VERSION,
    RENDERER_PROTOCOL_VERSION,
)
from app.preview.mirror import MirrorApplyError, RemoteTree
from app.preview.models import Endpoint, ServerInfo

__all__ = ["PreviewClient", "PreviewHandshakeError"]

#: A frame, including the newline, may not exceed this (mirrors the host).
MAX_FRAME_BYTES = 2 * 1024 * 1024


class PreviewHandshakeError(Exception):
    """The server rejected the session or spoke an unknown protocol."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = str(code)
        self.message = str(message)


class PreviewClient:
    """One live socket connection to a ``pydrud dev`` server."""

    def __init__(
        self,
        endpoint: Endpoint,
        tree: RemoteTree,
        *,
        on_state: Optional[Callable[[str, Optional[str]], None]] = None,
        on_transaction: Optional[Callable[[str, int], None]] = None,
        on_command: Optional[Callable[[dict], None]] = None,
        on_disconnect: Optional[Callable[[Optional[str]], None]] = None,
    ):
        self.endpoint = endpoint
        self.tree = tree
        self._on_state = on_state
        self._on_transaction = on_transaction
        self._on_command = on_command
        self._on_disconnect = on_disconnect

        self._sock: Optional[socket.socket] = None
        self._send_lock = threading.Lock()
        self._running = threading.Event()
        self._reader: Optional[threading.Thread] = None
        self._closed = False
        self.server: Optional[ServerInfo] = None

    # ── lifecycle ─────────────────────────────────────────────────────────

    def connect(self, *, metrics: Optional[dict] = None) -> ServerInfo:
        """Connect, authenticate and start the reader. Returns server info.

        Blocking — call it on a worker thread.
        """
        self._emit_state("connecting", None)
        family = socket.AF_INET
        sock = socket.socket(family, socket.SOCK_STREAM)
        sock.settimeout(CONNECT_TIMEOUT)
        try:
            sock.connect((self.endpoint.host, int(self.endpoint.port)))
        except OSError:
            sock.close()
            raise
        self._sock = sock
        self._emit_state("handshaking", None)

        self._send_raw(self._hello(metrics or {}))
        welcome = self._read_handshake_frame()
        self.server = self._validate_welcome(welcome)

        # Announce ourselves and hand the server our live window metrics so it
        # re-renders the layout for the real screen.
        self._send_event_raw({
            "type": "ready",
            "key": "",
            "data": {**(metrics or {}), "capabilities": dict(CLIENT_CAPABILITIES)},
        })

        self._running.set()
        self._reader = threading.Thread(
            target=self._read_loop, daemon=True, name="pydash-preview-reader")
        self._reader.start()
        return self.server

    def disconnect(self, reason: Optional[str] = "closed by user") -> None:
        """Close the connection and stop the reader (idempotent)."""
        self._closed = True
        self._running.clear()
        sock, self._sock = self._sock, None
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass

    # ── client → server ───────────────────────────────────────────────────

    def send_event(self, key: str, event: str, value: Any = None) -> None:
        """Forward a UI event (click/change/submit/scroll/…) to the server."""
        data = {} if value is None else {"value": value}
        self._send_event_raw({"type": str(event), "key": str(key), "data": data})

    def send_back(self) -> None:
        self._send_event_raw({"type": "back", "key": "", "data": {}})

    def send_metrics(self, metrics: dict) -> None:
        self._send_event_raw({"type": "metrics", "key": "", "data": dict(metrics)})

    def send_result(self, request_id: Any, ok: bool, *,
                    value: Any = None, error: Any = None) -> None:
        """Answer a service command that carried a request ``id``."""
        data: dict = {"id": request_id, "ok": bool(ok)}
        if ok:
            data["value"] = value
        else:
            data["error"] = error if error is not None else "unavailable"
        self._send_event_raw({"type": "result", "key": "", "data": data})

    # ── handshake helpers ─────────────────────────────────────────────────

    def _hello(self, metrics: dict) -> dict:
        return {
            "type": "preview_hello",
            "protocol": PREVIEW_PROTOCOL,
            "protocol_version": PREVIEW_PROTOCOL_VERSION,
            "renderer_protocol_version": RENDERER_PROTOCOL_VERSION,
            "session_id": self.endpoint.session_id,
            "token": self.endpoint.token,
            "client": {
                "name": CLIENT_NAME,
                "version": _client_version(),
                "platform": CLIENT_PLATFORM,
            },
            "capabilities": dict(CLIENT_CAPABILITIES),
            "last_revision": int(self.tree.revision),
            "metrics": _clean_metrics(metrics),
        }

    def _validate_welcome(self, message: dict) -> ServerInfo:
        kind = message.get("type")
        if kind == "preview_reject":
            raise PreviewHandshakeError(
                str(message.get("code") or "rejected"),
                str(message.get("message") or "the server rejected the session"))
        if kind != "preview_welcome":
            raise PreviewHandshakeError(
                "invalid_welcome", "the server did not send preview_welcome")
        if message.get("protocol") != PREVIEW_PROTOCOL:
            raise PreviewHandshakeError(
                "unsupported_protocol", "unknown preview protocol")
        if int(message.get("protocol_version", -1)) != PREVIEW_PROTOCOL_VERSION:
            raise PreviewHandshakeError(
                "unsupported_version", "unsupported preview protocol version")
        if int(message.get("renderer_protocol_version", -1)) \
                != RENDERER_PROTOCOL_VERSION:
            raise PreviewHandshakeError(
                "unsupported_renderer", "unsupported renderer protocol version")
        project = message.get("project") or {}
        return ServerInfo(
            project_id=str(project.get("id") or ""),
            project_name=str(project.get("name") or ""),
            session_id=str(message.get("session_id") or ""),
            port=int(message.get("port") or 0),
            capabilities=dict(message.get("capabilities") or {}),
            limits=dict(message.get("limits") or {}),
        )

    # ── reader ────────────────────────────────────────────────────────────

    def _read_loop(self) -> None:
        sock = self._sock
        reason: Optional[str] = None
        buffer = bytearray()
        try:
            while self._running.is_set() and sock is not None:
                chunk = sock.recv(65536)
                if not chunk:
                    reason = "the development server closed the connection"
                    break
                buffer.extend(chunk)
                if len(buffer) > MAX_FRAME_BYTES:
                    reason = "the server sent an oversized frame"
                    break
                while True:
                    newline = buffer.find(b"\n")
                    if newline < 0:
                        break
                    raw = bytes(buffer[:newline])
                    del buffer[:newline + 1]
                    self._handle_frame(raw)
        except OSError as exc:
            reason = str(exc)
        except Exception as exc:  # defensive: never kill the reader silently
            reason = str(exc)
        finally:
            self._running.clear()
            if not self._closed and self._on_disconnect is not None:
                self._on_disconnect(reason)

    def _handle_frame(self, raw: bytes) -> None:
        try:
            message = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return
        if not isinstance(message, dict):
            return
        cmd = message.get("cmd")
        if cmd == "render_transaction":
            self._handle_transaction(message)
        elif cmd:
            if self._on_command is not None:
                self._on_command(message)
        elif self._on_command is not None:
            self._on_command(message)

    def _handle_transaction(self, message: dict) -> None:
        tx_id = str(message.get("transaction_id") or "")
        kind = str(message.get("kind") or "")
        revision = _int(message.get("revision"), 0)
        base = _int(message.get("base_revision"), 0)
        if _int(message.get("protocol_version"), RENDERER_PROTOCOL_VERSION) \
                != RENDERER_PROTOCOL_VERSION:
            self._nack(tx_id, revision, "unsupported_version",
                       "renderer protocol version mismatch")
            return
        payload = {"tree": message.get("tree")} if kind == "snapshot" \
            else {"patches": message.get("patches")}
        try:
            ops = self.tree.apply(revision=revision, base_revision=base,
                                  kind=kind, payload=payload)
        except MirrorApplyError as exc:
            self._nack(tx_id, revision, "stale_base" if "stale_base" in str(exc)
                       else "apply_failed", str(exc))
            return
        self._send_event_raw({
            "type": "render_ack",
            "key": "",
            "data": {"transaction_id": tx_id, "revision": revision},
        })
        if self._on_transaction is not None:
            try:
                self._on_transaction(kind, ops)
            except Exception:
                # A UI-dispatch hiccup must never kill the reader: the tree is
                # already applied and ACKed, and the next transaction refreshes
                # the screen from the newest snapshot.
                pass

    def _nack(self, tx_id: str, revision: int, code: str, message: str) -> None:
        self._send_event_raw({
            "type": "render_nack",
            "key": "",
            "data": {
                "transaction_id": tx_id,
                "revision": revision,
                "native_revision": int(self.tree.revision),
                "code": code,
                "message": message,
                "recoverable": True,
            },
        })

    # ── wire helpers ──────────────────────────────────────────────────────

    def _read_handshake_frame(self) -> dict:
        """Read exactly one newline-terminated frame (no over-read)."""
        sock = self._sock
        assert sock is not None
        frame = bytearray()
        deadline_sock = sock
        deadline_sock.settimeout(HANDSHAKE_TIMEOUT)
        try:
            while len(frame) <= MAX_FRAME_BYTES:
                chunk = sock.recv(1)
                if not chunk:
                    raise PreviewHandshakeError(
                        "connection_closed",
                        "the server closed the connection during the handshake")
                frame.extend(chunk)
                if chunk == b"\n":
                    break
            else:
                raise PreviewHandshakeError(
                    "frame_too_large", "the welcome frame was too large")
        finally:
            try:
                sock.settimeout(None)
            except OSError:
                pass
        try:
            return json.loads(frame.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PreviewHandshakeError(
                "invalid_welcome", "the welcome frame was not valid JSON") from exc

    def _send_raw(self, message: dict) -> None:
        sock = self._sock
        if sock is None:
            return
        encoded = _encode(message)
        with self._send_lock:
            try:
                sock.sendall(encoded)
            except OSError:
                pass

    def _send_event_raw(self, message: dict) -> None:
        self._send_raw(message)

    def _emit_state(self, state: str, detail: Optional[str]) -> None:
        if self._on_state is not None:
            self._on_state(state, detail)


# ── module helpers ───────────────────────────────────────────────────────────


def _encode(message: dict) -> bytes:
    raw = json.dumps(message, separators=(",", ":"), ensure_ascii=False,
                     default=str)
    return (raw + "\n").encode("utf-8")


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _client_version() -> str:
    from app.config import APP_VERSION
    return APP_VERSION


#: Metric fields the host understands; anything else is dropped before sending.
_METRIC_FIELDS = (
    "width", "height", "width_px", "height_px", "density", "dpi", "text_scale",
    "orientation", "status_bar_height", "navigation_bar_height", "padding_top",
    "padding_right", "padding_bottom", "padding_left", "keyboard_height",
    "dark", "platform_version",
)


def _clean_metrics(metrics: dict) -> dict:
    cleaned: dict = {}
    for name in _METRIC_FIELDS:
        if name in metrics and metrics[name] is not None:
            cleaned[name] = metrics[name]
    return cleaned
