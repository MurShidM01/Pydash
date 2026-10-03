"""Pydash live preview — the client side of ``pydrud dev``.

Package layout:

* :mod:`app.preview.uri`      — parse & validate the QR payload (``pydrud://preview/connect?…``)
* :mod:`app.preview.models`   — connection states, endpoint & server metadata
* :mod:`app.preview.mirror`   — the mirrored remote widget tree + patch applier
* :mod:`app.preview.client`   — the socket client: handshake, transactions, events
* :mod:`app.preview.session`  — the session manager / state machine
* :mod:`app.preview.renderer` — renders the mirrored tree natively inside Pydash

The wire contract mirrors ``pydrud.core.preview`` / ``preview_server``
from the Pydrud 2.0.2 release: a versioned, authenticated preview
handshake followed by the existing renderer protocol (theme pushes,
revisioned render transactions, ACK/NACK, UI events).
"""

from app.preview.models import ConnectionState, Endpoint, ServerInfo
from app.preview.session import session
from app.preview.uri import PreviewUriError, parse_preview_uri

__all__ = [
    "ConnectionState", "Endpoint", "PreviewUriError", "ServerInfo",
    "parse_preview_uri", "session",
]
