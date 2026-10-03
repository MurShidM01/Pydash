"""A faithful miniature of Pydrud's ``pydrud dev`` preview server.

The real ``PreviewServer`` lives in the host-only ``pydrud.core.preview``
/ ``preview_server`` modules, which the framework deliberately keeps out
of the runtime bundled into apps. This harness reproduces its wire
behaviour — byte-wise hello read, the same validation rules and rejection
codes, the same welcome frame — and then hands the socket to a *real*
:class:`pydrud.App` via ``serve_transport``, so the entire render
pipeline in these tests is the genuine SDK.

It is used by ``tests/test_preview_protocol.py`` to exercise Pydash's
client end to end without a developer machine.
"""

from __future__ import annotations

import hmac
import json
import secrets
import socket
import threading
import time
import uuid
from dataclasses import dataclass

from pydrud.core.protocol import MAX_FRAME_BYTES, decode_envelope

from app.config import (
    CLIENT_CAPABILITIES,
    PREVIEW_PROTOCOL,
    PREVIEW_PROTOCOL_VERSION,
    RENDERER_PROTOCOL_VERSION,
)

HANDSHAKE_TIMEOUT = 10.0

#: Mirrors pydrud.core.preview.SERVER_CAPABILITIES.
SERVER_CAPABILITIES = {
    "host_python": True,
    "file_watching": True,
    "stateful_hot_reload": True,
    "initial_snapshot": True,
    "incremental_patches": True,
    "reconnect_resync": True,
}

#: Mirrors pydrud.core.preview.REQUIRED_RENDERER_CAPABILITIES.
REQUIRED_RENDERER_CAPABILITIES = frozenset({
    "transactional_render",
    "revisioned_render",
    "ack_nack",
    "resync",
})


class HarnessProtocolError(ValueError):
    """Raised with one of the server's rejection codes."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = str(code)
        self.message = str(message)


@dataclass(frozen=True)
class HarnessSession:
    """Session identity + bearer credential for one run."""

    project_id: str
    project_name: str
    session_id: str
    token: str

    @classmethod
    def create(cls, project_id: str = "local.harness",
               project_name: str = "Harness Project") -> "HarnessSession":
        return cls(
            project_id=project_id,
            project_name=project_name,
            session_id=str(uuid.uuid4()),
            token=secrets.token_urlsafe(32),
        )


def welcome_message(session: HarnessSession, port: int) -> dict:
    return {
        "type": "preview_welcome",
        "protocol": PREVIEW_PROTOCOL,
        "protocol_version": PREVIEW_PROTOCOL_VERSION,
        "renderer_protocol_version": RENDERER_PROTOCOL_VERSION,
        "session_id": session.session_id,
        "project": {"id": session.project_id, "name": session.project_name},
        "port": int(port),
        "capabilities": dict(SERVER_CAPABILITIES),
        "limits": {"max_frame_bytes": MAX_FRAME_BYTES},
    }


def validate_client_hello(message, session: HarnessSession) -> dict:
    """The same checks ``pydrud dev`` makes, in the same order."""
    if not isinstance(message, dict):
        raise HarnessProtocolError("invalid_hello", "hello must be an object")
    if message.get("type") != "preview_hello":
        raise HarnessProtocolError("invalid_hello",
                                   "first frame must be preview_hello")
    if message.get("protocol") != PREVIEW_PROTOCOL:
        raise HarnessProtocolError("invalid_hello",
                                   "unknown preview protocol")
    version = _integer(message.get("protocol_version"), "protocol_version")
    if version != PREVIEW_PROTOCOL_VERSION:
        raise HarnessProtocolError(
            "unsupported_version",
            f"expected preview protocol {PREVIEW_PROTOCOL_VERSION}, "
            f"got {version}")
    renderer = _integer(message.get("renderer_protocol_version"),
                        "renderer_protocol_version")
    if renderer != RENDERER_PROTOCOL_VERSION:
        raise HarnessProtocolError(
            "unsupported_renderer",
            f"expected renderer protocol {RENDERER_PROTOCOL_VERSION}, "
            f"got {renderer}")
    if not hmac.compare_digest(str(message.get("session_id") or ""),
                               session.session_id):
        raise HarnessProtocolError("authentication_failed",
                                   "invalid session or token")
    if not hmac.compare_digest(str(message.get("token") or ""),
                               session.token):
        raise HarnessProtocolError("authentication_failed",
                                   "invalid session or token")

    capabilities = message.get("capabilities")
    if not isinstance(capabilities, dict):
        raise HarnessProtocolError("missing_capabilities",
                                   "client capabilities must be an object")
    missing = sorted(name for name in REQUIRED_RENDERER_CAPABILITIES
                     if capabilities.get(name) is not True)
    if missing:
        raise HarnessProtocolError(
            "missing_capabilities",
            "client is missing required renderer capabilities: "
            + ", ".join(missing))

    metrics = message.get("metrics") or {}
    if not isinstance(metrics, dict):
        raise HarnessProtocolError("invalid_metrics",
                                   "metrics must be an object")

    revision = _integer(message.get("last_revision", 0), "last_revision")
    if revision < 0:
        raise HarnessProtocolError("invalid_revision",
                                   "last_revision is out of range")

    client = message.get("client") or {}
    if not isinstance(client, dict):
        raise HarnessProtocolError("invalid_client",
                                   "client metadata must be an object")
    return {"capabilities": dict(capabilities),
            "metrics": dict(metrics),
            "last_revision": revision}


def _integer(value, name: str) -> int:
    if isinstance(value, bool) or value is None:
        raise HarnessProtocolError("invalid_hello",
                                   f"{name} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise HarnessProtocolError("invalid_hello",
                                   f"{name} must be an integer") from exc


class PreviewServerHarness:
    """Accepts one Pydash client and serves a real App to it."""

    def __init__(self, app, session: HarnessSession, *, host: str = "127.0.0.1",
                 port: int = 0):
        self.app = app
        self.session = session
        self.host = host
        self.port = port
        self.status: list = []          # (event, kwargs) notifications
        self._listener: socket.socket | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # ── lifecycle ─────────────────────────────────────────────────────────

    def start(self) -> "PreviewServerHarness":
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((self.host, self.port))
        listener.listen(4)
        listener.settimeout(0.25)
        self._listener = listener
        self.port = listener.getsockname()[1]
        self._thread = threading.Thread(target=self._serve, daemon=True,
                                        name="preview-harness")
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        listener, self._listener = self._listener, None
        if listener is not None:
            try:
                listener.close()
            except OSError:
                pass
        if self._thread is not None:
            self._thread.join(timeout=2)

    def __enter__(self) -> "PreviewServerHarness":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()

    # ── serving ───────────────────────────────────────────────────────────

    def _serve(self) -> None:
        while not self._stop.is_set():
            assert self._listener is not None
            try:
                client, _peer = self._listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            worker = threading.Thread(target=self._serve_client,
                                      args=(client,), daemon=True)
            worker.start()

    def _serve_client(self, client: socket.socket) -> None:
        try:
            client.settimeout(HANDSHAKE_TIMEOUT)
            raw = _read_frame(client)
            try:
                hello = decode_envelope(raw)
            except Exception as exc:
                raise HarnessProtocolError("invalid_hello", str(exc)) from exc
            try:
                normalized = validate_client_hello(hello, self.session)
            except HarnessProtocolError as exc:
                _send_message(client, {
                    "type": "preview_reject",
                    "protocol": PREVIEW_PROTOCOL,
                    "protocol_version": PREVIEW_PROTOCOL_VERSION,
                    "code": exc.code,
                    "message": exc.message,
                })
                client.close()
                self.status.append(("rejected", {"code": exc.code}))
                return

            client.settimeout(None)
            _send_message(client, welcome_message(self.session, self.port))
            self.status.append(("connected",
                                {"client": hello.get("client", {})}))
            self.app.serve_transport(
                client,
                capabilities=normalized["capabilities"],
                metrics=normalized["metrics"],
                native_revision=normalized["last_revision"],
            )
        except OSError:
            pass
        finally:
            try:
                client.close()
            except OSError:
                pass


def _read_frame(sock: socket.socket) -> str:
    """Read one newline-terminated frame byte-wise (as the real server)."""
    frame = bytearray()
    while len(frame) <= MAX_FRAME_BYTES:
        chunk = sock.recv(1)
        if not chunk:
            raise ConnectionError("closed during handshake")
        frame.extend(chunk)
        if chunk == b"\n":
            return frame.decode("utf-8")
    raise HarnessProtocolError("frame_too_large", "handshake frame too large")


def _send_message(sock: socket.socket, message: dict) -> None:
    sock.sendall((json.dumps(message) + "\n").encode("utf-8"))
