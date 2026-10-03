"""The preview socket client — Pydash's side of the ``pydrud dev`` protocol.

One :class:`PreviewClient` owns one TCP connection to the development
server. The conversation is:

1. connect to ``host:port``;
2. send ``preview_hello`` (protocol versions, session credentials,
   renderer capabilities, device metrics, last known revision);
3. read ``preview_welcome`` — or ``preview_reject`` and give up;
4. send ``ready`` with live metrics, exactly like the native bridge does;
5. from here on speak the regular Pydrud renderer protocol:

   * server → client: ``theme`` pushes and revisioned
     ``render_transaction`` frames (snapshots and patches), plus page
     commands (toast, snackbar, dialogs, …) carrying a ``request_id``;
   * client → server: ``render_ack`` / ``render_nack`` after applying a
     transaction, UI events from the previewed widgets, ``metrics`` on
     window changes, ``back`` presses and ``result`` replies for native
     service calls executed on the device.

Everything runs on a dedicated reader thread; callbacks are invoked there
and must marshal onto the UI thread themselves (the session layer does).
"""

from __future__ import annotations

import json
import socket
import threading
from typing import Any, Callable, Optional

from pydrud.core.protocol import (
    MAX_FRAME_BYTES,
    ProtocolError,
    decode_envelope,
    encode_envelope,
)

from app.config import (
    CLIENT_CAPABILITIES,
    CLIENT_NAME,
    CLIENT_PLATFORM,
    APP_VERSION,
    CONNECT_TIMEOUT,
    HANDSHAKE_TIMEOUT,
    PREVIEW_PROTOCOL,
    PREVIEW_PROTOCOL_VERSION,
    RENDERER_PROTOCOL_VERSION,
)
from app.preview.models import Endpoint, ServerInfo
from app.preview.mirror import MirrorApplyError, RemoteTree

__all__ = ["PreviewClient", "PreviewHandshakeError"]


class PreviewHandshakeError(RuntimeError):
    """The server refused the session (or the handshake was malformed)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = str(code)
        self.message = str(message)


class PreviewClient:
    """Speaks the preview protocol against one development server."""

    def __init__(
        self,
        endpoint: Endpoint,
        tree: RemoteTree,
        *,
        on_state: Optional[Callable[[str, Optional[str]], None]] = None,
        on_transaction: Optional[Callable[[str, int], None]] = None,
        on_event: Optional[Callable[[str, str, dict], None]] = None,
        on_command: Optional[Callable[[dict], None]] = None,
        on_disconnect: Optional[Callable[[Optional[str]], None]] = None,
    ):
        self.endpoint = endpoint
        self.tree = tree
        self._on_state = on_state or (lambda state, detail: None)
        self._on_transaction = on_transaction or (lambda kind, ops: None)
        self._on_event = on_event or (lambda kind, key, data: None)
        self._on_command = on_command or (lambda message: None)
        self._on_disconnect = on_disconnect or (lambda reason: None)

        self.server: Optional[ServerInfo] = None
        self._sock: Optional[socket.socket] = None
        self._send_lock = threading.Lock()
        self._running = threading.Event()
        self._connected = threading.Event()
        self._reader: Optional[threading.Thread] = None

    # ── lifecycle ─────────────────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        return self._connected.is_set()

    def connect(self, *, metrics: Optional[dict] = None) -> ServerInfo:
        """Connect, handshake and start the reader loop.

        Returns the parsed ``preview_welcome`` payload. Raises
        :class:`PreviewHandshakeError` when the server rejects the session
        and :class:`OSError`/``socket.timeout`` for network failures.
        """
        self._running.set()
        self._emit_state("connecting")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(CONNECT_TIMEOUT)
        try:
            sock.connect((self.endpoint.host, self.endpoint.port))
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        except OSError:
            sock.close()
            raise

        self._sock = sock
        self._connected.set()  # the handshake itself sends hello + ready
        try:
            self._emit_state("handshaking")
            self._handshake(sock, metrics or {})
        except Exception:
            self._connected.clear()
            self._close_socket()
            raise

        self._reader = threading.Thread(
            target=self._read_loop, args=(sock,), daemon=True,
            name="pydash-preview-client")
        self._reader.start()
        return self.server or ServerInfo()

    def disconnect(self, reason: Optional[str] = None) -> None:
        """Close the session from our side."""
        self._running.clear()
        self._connected.clear()
        self._close_socket()
        self._on_disconnect(reason)

    # ── handshake ─────────────────────────────────────────────────────────

    def _handshake(self, sock: socket.socket, metrics: dict) -> None:
        hello = {
            "type": "preview_hello",
            "protocol": PREVIEW_PROTOCOL,
            "protocol_version": PREVIEW_PROTOCOL_VERSION,
            "renderer_protocol_version": RENDERER_PROTOCOL_VERSION,
            "session_id": self.endpoint.session_id,
            "token": self.endpoint.token,
            "capabilities": dict(CLIENT_CAPABILITIES),
            "metrics": _clean_metrics(metrics),
            "last_revision": self.tree.revision,
            "client": {
                "name": CLIENT_NAME,
                "version": APP_VERSION,
                "platform": CLIENT_PLATFORM,
            },
        }
        _send_frame(sock, hello)

        sock.settimeout(HANDSHAKE_TIMEOUT)
        raw = _read_frame(sock)
        try:
            reply = decode_envelope(raw)
        except ProtocolError as exc:
            raise PreviewHandshakeError(
                "invalid_welcome", f"Malformed server reply: {exc}") from exc
        if reply is None:
            raise PreviewHandshakeError(
                "invalid_welcome", "Empty server reply.")
        kind = reply.get("type")

        if kind == "preview_reject":
            raise PreviewHandshakeError(
                str(reply.get("code") or "rejected"),
                str(reply.get("message") or "The server refused the session."))
        if kind != "preview_welcome":
            raise PreviewHandshakeError(
                "invalid_welcome",
                f"Unexpected first frame {kind!r} from the server.")

        version = int(reply.get("protocol_version", 0) or 0)
        if version != PREVIEW_PROTOCOL_VERSION:
            raise PreviewHandshakeError(
                "unsupported_version",
                f"Server speaks preview protocol {version}; Pydash speaks "
                f"{PREVIEW_PROTOCOL_VERSION}.")
        renderer = int(reply.get("renderer_protocol_version", 0) or 0)
        if renderer != RENDERER_PROTOCOL_VERSION:
            raise PreviewHandshakeError(
                "unsupported_renderer",
                f"Server speaks renderer protocol {renderer}; Pydash speaks "
                f"{RENDERER_PROTOCOL_VERSION}.")

        project = reply.get("project") or {}
        self.server = ServerInfo(
            project_id=str(project.get("id") or self.endpoint.project_id),
            project_name=str(project.get("name") or self.endpoint.project_name),
            session_id=str(reply.get("session_id") or self.endpoint.session_id),
            port=int(reply.get("port") or self.endpoint.port),
            capabilities=dict(reply.get("capabilities") or {}),
            limits=dict(reply.get("limits") or {}),
        )

        # Mirror the native bridge: announce real metrics so the project
        # lays itself out for this exact screen, then the server re-renders.
        sock.settimeout(None)
        self.send_event("ready", "", {
            **_clean_metrics(metrics),
            "protocol_version": RENDERER_PROTOCOL_VERSION,
            "capabilities": dict(CLIENT_CAPABILITIES),
        })

    # ── reader loop ───────────────────────────────────────────────────────

    def _read_loop(self, sock: socket.socket) -> None:
        buffer = b""
        try:
            while self._running.is_set():
                try:
                    chunk = sock.recv(65536)
                except OSError:
                    break
                if not chunk:
                    break
                buffer += chunk
                if len(buffer) > MAX_FRAME_BYTES and b"\n" not in buffer:
                    self._protocol_failure(
                        f"bridge frame exceeds {MAX_FRAME_BYTES} bytes")
                    break
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if len(line) + 1 > MAX_FRAME_BYTES:
                        self._protocol_failure(
                            f"bridge frame exceeds {MAX_FRAME_BYTES} bytes")
                        return
                    text = line.decode("utf-8", errors="replace").strip()
                    if not text:
                        continue
                    if not self._handle_line(text):
                        return
        except Exception:
            pass
        finally:
            was_connected = self._connected.is_set()
            self._connected.clear()
            if self._sock is sock:
                self._sock = None
            try:
                sock.close()
            except OSError:
                pass
            if self._running.is_set() and was_connected:
                # Unexpected loss — the session layer decides about retries.
                self._on_disconnect(None)

    def _handle_line(self, text: str) -> bool:
        """Route one server frame. Returns False to stop the reader."""
        try:
            message = decode_envelope(text)
        except ProtocolError as exc:
            self._protocol_failure(f"invalid JSON frame: {exc}")
            return False
        if message is None:
            return True

        cmd = message.get("cmd")
        if cmd == "render_transaction":
            self._handle_transaction(message)
            return True
        # Everything else (theme, toast, snackbar, dialogs with a
        # request_id, back_result, …) is handled by the renderer layer.
        try:
            self._on_command(message)
        except Exception:
            pass
        return True

    # ── render transactions ───────────────────────────────────────────────

    def _handle_transaction(self, message: dict) -> None:
        tx_id = str(message.get("transaction_id") or "")
        revision = _as_int(message.get("revision"), -1)
        base = _as_int(message.get("base_revision"), -1)
        kind = str(message.get("kind") or "")

        if not tx_id or revision < 0 or base < 0:
            self._nack(tx_id, revision, "invalid_transaction")
            return
        version = _as_int(message.get("protocol_version"), 0)
        if version != RENDERER_PROTOCOL_VERSION:
            self._protocol_failure(
                f"unsupported renderer protocol {version}")
            self._nack(tx_id, revision, "unsupported_version")
            return

        payload: dict = {}
        if kind == "snapshot":
            payload = {"tree": message.get("tree")}
        elif kind == "patch":
            payload = {"patches": message.get("patches")}
        else:
            self._nack(tx_id, revision, "unknown_transaction_kind")
            return

        try:
            ops = self.tree.apply(revision=revision, base_revision=base,
                                  kind=kind, payload=payload)
        except (MirrorApplyError, ValueError) as exc:
            reason = getattr(exc, "reason", None) or str(exc)
            if str(reason).startswith("stale_base_revision"):
                reason = "stale_base_revision"
            self._nack(tx_id, revision, reason)
            return

        self._ack(tx_id, revision)
        try:
            self._on_transaction(kind, ops)
        except Exception:
            pass

    def _ack(self, tx_id: str, revision: int) -> None:
        self._send({
            "type": "render_ack",
            "key": "",
            "data": {"transaction_id": tx_id, "revision": revision},
        })

    def _nack(self, tx_id: str, revision: int, reason: str) -> None:
        self._send({
            "type": "render_nack",
            "key": "",
            "data": {
                "transaction_id": tx_id,
                "revision": revision,
                "native_revision": self.tree.revision,
                "reason": reason,
                "recoverable": True,
            },
        })

    # ── client → server ───────────────────────────────────────────────────

    def send_event(self, kind: str, key: str, data: Optional[dict] = None) -> bool:
        """Forward a UI event from the previewed project to the server."""
        return self._send({
            "type": str(kind),
            "key": str(key),
            "data": dict(data or {}),
        })

    def send_back(self) -> bool:
        """Offer a hardware back press to the previewed project."""
        return self.send_event("back", "")

    def send_metrics(self, metrics: dict) -> bool:
        """Tell the server the window changed (rotation, insets, …)."""
        return self._send({
            "type": "metrics", "key": "", "data": _clean_metrics(metrics),
        })

    def send_result(self, request_id: str, *, ok: bool,
                    value: Any = None, error: Optional[str] = None) -> bool:
        """Answer a native service call the previewed project requested."""
        data: dict = {"request_id": str(request_id), "ok": bool(ok)}
        if ok:
            data["value"] = value
        else:
            data["error"] = str(error or "native call failed")
        return self._send({"type": "result", "key": "", "data": data})

    def _send(self, message: dict) -> bool:
        sock = self._sock
        if sock is None or not self._connected.is_set():
            return False
        try:
            with self._send_lock:
                sock.sendall(encode_envelope(message).encode("utf-8"))
            return True
        except (OSError, ProtocolError):
            return False

    # ── internals ─────────────────────────────────────────────────────────

    def _emit_state(self, state: str) -> None:
        try:
            self._on_state(state, None)
        except Exception:
            pass

    def _protocol_failure(self, reason: str) -> None:
        self._on_command({
            "cmd": "_pydash_protocol_error", "message": reason,
        })

    def _close_socket(self) -> None:
        sock, self._sock = self._sock, None
        if sock is None:
            return
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            sock.close()
        except OSError:
            pass


# ── frame helpers ───────────────────────────────────────────────────────────


def _read_frame(sock: socket.socket) -> str:
    """Read one newline-terminated frame without over-buffering."""
    frame = bytearray()
    while len(frame) <= MAX_FRAME_BYTES:
        chunk = sock.recv(1)
        if not chunk:
            raise ConnectionError("connection closed during handshake")
        frame.extend(chunk)
        if chunk == b"\n":
            return frame.decode("utf-8")
    raise PreviewHandshakeError(
        "frame_too_large", f"handshake frame exceeds {MAX_FRAME_BYTES} bytes")


def _send_frame(sock: socket.socket, message: dict) -> None:
    sock.sendall(encode_envelope(message).encode("utf-8"))


def _as_int(value, default: int) -> int:
    """Coerce a JSON number to int without mistaking 0 for missing."""
    if isinstance(value, bool) or value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clean_metrics(metrics: dict) -> dict:
    """Keep only the numeric/boolean metrics fields the server accepts."""
    allowed = {
        "width", "height", "width_px", "height_px", "density", "dpi",
        "xdpi", "ydpi", "text_scale", "status_bar_height",
        "navigation_bar_height", "padding_top", "padding_right",
        "padding_bottom", "padding_left", "keyboard_height", "refresh_rate",
        "smallest_width", "sdk",
    }
    out: dict = {}
    for name in allowed:
        if metrics.get(name) is not None:
            try:
                out[name] = float(metrics[name])
            except (TypeError, ValueError):
                continue
    if metrics.get("dark") is not None:
        out["dark"] = bool(metrics["dark"])
    for name in ("orientation", "ui_mode", "model"):
        if metrics.get(name) is not None:
            out[name] = str(metrics[name])
    return out
