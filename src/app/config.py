"""Pydash identity, versions and protocol constants.

Pydash is the live-preview companion app for Pydrud: a developer runs
``pydrud dev`` on their machine, scans the QR code from Pydash, and the
project's UI renders natively inside Pydash — with no APK rebuilds.

This module is the single source of truth for names, versions and the
wire-protocol constants the preview client speaks. Keep it free of widget
imports so any layer (protocol, UI, tests) can read it.
"""

from __future__ import annotations

import pydrud

#: ── Identity ────────────────────────────────────────────────────────────────
APP_NAME = "Pydash"
APP_TAGLINE = "Live UI preview for Pydrud"
APP_VERSION = "1.0.0"

#: The brand colour the whole design system is generated from. It matches
#: the seed in ``pydrud.toml``; the user can re-seed it from Settings.
ACCENT = "#FF6366F1"
#: A second brand colour used for gradients and accents.
ACCENT_ALT = "#FF14B8A6"

#: ── Project links ───────────────────────────────────────────────────────────
PYDRUD_REPO = "https://github.com/MurShidM01/Pydrud"
PYDASH_REPO = "https://github.com/MurShidM01/Pydash"
PYDRUD_DOCS = "https://github.com/MurShidM01/Pydrud#readme"

#: ── Framework versions (reported in Settings → About) ──────────────────────
PYDRUD_VERSION = pydrud.__version__

#: ── Wire protocol ───────────────────────────────────────────────────────────
#: The preview handshake is versioned separately from the renderer protocol.
#: These constants mirror ``pydrud.core.protocol`` and the host preview
#: server contract shipped with Pydrud 2.0.2 (``pydrud dev``).
from pydrud.core.protocol import PROTOCOL_VERSION as RENDERER_PROTOCOL_VERSION  # noqa: E402

PREVIEW_PROTOCOL = "pydrud.preview"
PREVIEW_PROTOCOL_VERSION = 1
#: Default TCP port ``pydrud dev`` listens on.
DEFAULT_PREVIEW_PORT = 8597
#: The QR payload scheme/authority/path printed by ``pydrud dev``.
PREVIEW_SCHEME = "pydrud"
PREVIEW_AUTHORITY = "preview"
PREVIEW_PATH = "/connect"

#: Capabilities the host server requires a renderer to declare. They match
#: what the generated Android bridge advertises in its ``ready`` event.
CLIENT_CAPABILITIES = {
    "transactional_render": True,
    "revisioned_render": True,
    "ack_nack": True,
    "resync": True,
    "coalescing": True,
    "native_animation_clock": True,
}

#: How Pydash identifies itself in the ``preview_hello`` frame.
CLIENT_NAME = "Pydash"
CLIENT_PLATFORM = "android"

#: ── Connection behaviour ────────────────────────────────────────────────────
CONNECT_TIMEOUT = 8.0        # seconds to establish the TCP connection
HANDSHAKE_TIMEOUT = 10.0     # seconds to wait for preview_welcome
RECONNECT_BASE_DELAY = 0.6   # first auto-reconnect delay (seconds)
RECONNECT_MAX_DELAY = 8.0    # backoff ceiling
RECONNECT_MAX_ATTEMPTS = 12

#: Prefixed onto every Pydash-owned widget key so the mirrored remote tree
#: (whose keys arrive verbatim from the dev server) can never collide with
#: the client's own chrome.
KEY_PREFIX = "pd_"

__all__ = [
    "ACCENT", "ACCENT_ALT", "APP_NAME", "APP_TAGLINE", "APP_VERSION",
    "CLIENT_CAPABILITIES", "CLIENT_NAME", "CLIENT_PLATFORM",
    "CONNECT_TIMEOUT", "DEFAULT_PREVIEW_PORT", "HANDSHAKE_TIMEOUT",
    "KEY_PREFIX", "PREVIEW_AUTHORITY", "PREVIEW_PATH", "PREVIEW_PROTOCOL",
    "PREVIEW_PROTOCOL_VERSION", "PREVIEW_SCHEME", "PYDASH_REPO",
    "PYDRUD_DOCS", "PYDRUD_REPO", "PYDRUD_VERSION",
    "RECONNECT_BASE_DELAY", "RECONNECT_MAX_ATTEMPTS", "RECONNECT_MAX_DELAY",
    "RENDERER_PROTOCOL_VERSION",
]
