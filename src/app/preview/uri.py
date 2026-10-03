"""Preview URI parsing — the QR payload printed by ``pydrud dev``.

``pydrud dev`` encodes one URI that carries everything Pydash needs to
reach the development server::

    pydrud://preview/connect?host=192.168.1.20&port=8597
        &session=<uuid>&token=<urlsafe-secret>&protocol=1&renderer=2
        &project=<id>&name=<project name>

This module is the client-side mirror of the host's
``pydrud.core.preview`` contract (Pydrud 2.0.2): the same scheme,
authority, path, parameter names and validation rules. Keeping a local
copy is intentional — the host-only preview modules are excluded from the
runtime bundled into the APK, and the client must not depend on them.
"""

from __future__ import annotations

import ipaddress
import urllib.parse
from dataclasses import dataclass
from typing import Any

from app.config import (
    DEFAULT_PREVIEW_PORT,
    PREVIEW_AUTHORITY,
    PREVIEW_PATH,
    PREVIEW_PROTOCOL_VERSION,
    PREVIEW_SCHEME,
    RENDERER_PROTOCOL_VERSION,
)

__all__ = ["PreviewUriError", "parse_preview_uri", "normalise_uri"]


class PreviewUriError(ValueError):
    """A QR payload that is not a valid Pydrud preview URI.

    ``code`` matches the vocabulary the server uses when it rejects a
    handshake, so the UI can show one consistent set of diagnostics.
    """

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = str(code)
        self.message = str(message)


@dataclass(frozen=True)
class PreviewTarget:
    """A validated preview endpoint plus its session credentials."""

    host: str
    port: int
    session_id: str
    token: str
    project_id: str
    project_name: str
    protocol_version: int
    renderer_protocol_version: int

    def describe(self) -> str:
        """Human-readable ``host:port`` label for status surfaces."""
        return f"{self.host}:{self.port}"


def parse_preview_uri(uri: str) -> PreviewTarget:
    """Parse and validate a Pydrud preview QR payload.

    Raises :class:`PreviewUriError` with a machine-readable ``code`` for
    anything the host server would also refuse — wrong scheme, missing
    parameter, version mismatch, or an unconnectable host.
    """
    parsed = urllib.parse.urlparse(str(uri))
    if (parsed.scheme != PREVIEW_SCHEME
            or parsed.netloc != PREVIEW_AUTHORITY
            or parsed.path != PREVIEW_PATH):
        raise PreviewUriError(
            "invalid_uri",
            "Not a Pydrud preview code. Run `pydrud dev` and scan the "
            "QR code it prints.")

    try:
        values = urllib.parse.parse_qs(parsed.query, strict_parsing=True)
    except ValueError as exc:
        raise PreviewUriError(
            "invalid_uri", "Malformed preview code.") from exc

    def one(name: str) -> str:
        found = values.get(name, [])
        if len(found) != 1 or not found[0]:
            raise PreviewUriError(
                "invalid_uri", f"Preview code is missing '{name}'.")
        return found[0]

    protocol = _integer(one("protocol"), "protocol")
    renderer = _integer(one("renderer"), "renderer")
    if protocol != PREVIEW_PROTOCOL_VERSION:
        raise PreviewUriError(
            "unsupported_version",
            f"Preview protocol {protocol} is not supported "
            f"(Pydash speaks {PREVIEW_PROTOCOL_VERSION}). "
            "Update Pydrud or Pydash.")
    if renderer != RENDERER_PROTOCOL_VERSION:
        raise PreviewUriError(
            "unsupported_renderer",
            f"Renderer protocol {renderer} is not supported "
            f"(Pydash speaks {RENDERER_PROTOCOL_VERSION}).")

    try:
        host = _connectable_host(one("host"))
        port = _port(_integer(one("port"), "port"))
    except ValueError as exc:
        raise PreviewUriError("invalid_uri", str(exc)) from exc

    return PreviewTarget(
        host=host,
        port=port,
        session_id=one("session"),
        token=one("token"),
        project_id=one("project"),
        project_name=one("name"),
        protocol_version=protocol,
        renderer_protocol_version=renderer,
    )


def normalise_uri(text: str) -> str:
    """Tidy manually-entered text into a URI Pydash can parse.

    Users paste the connection URI from the terminal, sometimes with
    surrounding quotes, whitespace or a clipboard label; make a best
    effort before validation so manual entry feels forgiving.
    """
    cleaned = str(text or "").strip().strip("'\"`").strip()
    if not cleaned:
        return cleaned
    if not cleaned.startswith(f"{PREVIEW_SCHEME}://"):
        # Some terminals and chat apps strip the scheme when copying.
        if cleaned.startswith(f"{PREVIEW_AUTHORITY}{PREVIEW_PATH}"):
            cleaned = f"{PREVIEW_SCHEME}://{cleaned}"
    return cleaned


# ── validators (mirrors of the host's rules) ────────────────────────────────


def _integer(value: Any, name: str) -> int:
    if isinstance(value, bool):
        raise PreviewUriError("invalid_uri", f"'{name}' must be a number.")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise PreviewUriError(
            "invalid_uri", f"'{name}' must be a number.") from exc


def _port(value: Any) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise PreviewUriError(
            "invalid_uri", "Preview port must be a number.") from exc
    if not 1 <= port <= 65535:
        raise PreviewUriError(
            "invalid_uri", "Preview port must be between 1 and 65535.")
    return port


def _connectable_host(value: Any) -> str:
    host = str(value or "").strip().strip("[]")
    if not host or host in {"0.0.0.0", "::"}:
        raise PreviewUriError(
            "invalid_uri",
            "The QR code contains an unconnectable address. Start "
            "`pydrud dev --connect-host <your-LAN-IP>` and scan again.")
    if any(ch.isspace() for ch in host) or "/" in host:
        raise PreviewUriError("invalid_uri", "Invalid preview host.")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        if len(host) > 253 or any(not label for label in host.split(".")):
            raise PreviewUriError("invalid_uri", "Invalid preview hostname.")
    return host
