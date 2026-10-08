"""Connection states and metadata for the live preview session."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

__all__ = ["ConnectionState", "Endpoint", "ServerInfo", "SessionStats", "STATES",
           "STATE_HINTS", "STATE_LABELS"]


class ConnectionState:
    """The lifecycle of a preview session, as one set of string constants.

    String values (not an enum) so they serialise cleanly into State objects
    and render directly in the UI.
    """

    IDLE = "idle"                  #: never connected, nothing pending
    CONNECTING = "connecting"      #: TCP connection in flight
    HANDSHAKING = "handshaking"    #: connected, waiting for preview_welcome
    CONNECTED = "connected"        #: session live, tree rendered
    SYNCING = "syncing"            #: applying a render transaction
    RECONNECTING = "reconnecting"  #: link dropped, retrying automatically
    FAILED = "failed"              #: gave up (or the server refused us)
    DISCONNECTED = "disconnected"  #: closed by the user


#: Ordered list for iteration / tests.
STATES = (
    ConnectionState.IDLE,
    ConnectionState.CONNECTING,
    ConnectionState.HANDSHAKING,
    ConnectionState.CONNECTED,
    ConnectionState.SYNCING,
    ConnectionState.RECONNECTING,
    ConnectionState.FAILED,
    ConnectionState.DISCONNECTED,
)

#: Friendly, non-technical labels for the dashboard.
STATE_LABELS = {
    ConnectionState.IDLE: "Not connected",
    ConnectionState.CONNECTING: "Connecting…",
    ConnectionState.HANDSHAKING: "Verifying session…",
    ConnectionState.CONNECTED: "Connected",
    ConnectionState.SYNCING: "Syncing UI…",
    ConnectionState.RECONNECTING: "Reconnecting…",
    ConnectionState.FAILED: "Connection failed",
    ConnectionState.DISCONNECTED: "Disconnected",
}

#: One-line explanations shown under the label.
STATE_HINTS = {
    ConnectionState.IDLE: "Scan the QR code printed by `pydrud dev`.",
    ConnectionState.CONNECTING: "Reaching the development server on your LAN.",
    ConnectionState.HANDSHAKING: "Checking protocol versions and credentials.",
    ConnectionState.CONNECTED: "Edit Python on your computer — this screen follows.",
    ConnectionState.SYNCING: "Applying the latest UI update.",
    ConnectionState.RECONNECTING: "The link dropped. Pydash is retrying.",
    ConnectionState.FAILED: "The development server could not be reached.",
    ConnectionState.DISCONNECTED: "The preview session was closed.",
}


@dataclass
class Endpoint:
    """Where to connect and the one-run credentials from the QR code."""

    host: str
    port: int
    session_id: str
    token: str
    project_id: str = ""
    project_name: str = ""

    def describe(self) -> str:
        return f"{self.host}:{self.port}"

    def as_dict(self) -> dict:
        return {
            "host": self.host, "port": self.port,
            "session_id": self.session_id, "token": self.token,
            "project_id": self.project_id,
            "project_name": self.project_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Endpoint":
        return cls(
            host=str(data.get("host", "")),
            port=int(data.get("port", 0) or 0),
            session_id=str(data.get("session_id", "")),
            token=str(data.get("token", "")),
            project_id=str(data.get("project_id", "")),
            project_name=str(data.get("project_name", "")),
        )


@dataclass
class ServerInfo:
    """What the server told us about itself in ``preview_welcome``."""

    project_id: str = ""
    project_name: str = ""
    session_id: str = ""
    port: int = 0
    capabilities: dict = field(default_factory=dict)
    limits: dict = field(default_factory=dict)
    #: Pydrud release running on the developer machine, when reported.
    host_version: str = ""


@dataclass
class SessionStats:
    """Live counters shown in the dashboard and preview header."""

    revision: int = 0
    snapshots: int = 0
    patches: int = 0
    applied_ops: int = 0
    events_sent: int = 0
    #: monotonic timestamp of the last accepted transaction
    last_sync: Optional[float] = None

    def mark_sync(self, kind: str, ops: int = 0) -> None:
        self.last_sync = time.monotonic()
        if kind == "snapshot":
            self.snapshots += 1
        else:
            self.patches += 1
            self.applied_ops += ops

    @property
    def last_sync_age(self) -> Optional[float]:
        """Seconds since the last sync (None before the first one)."""
        if self.last_sync is None:
            return None
        return max(0.0, time.monotonic() - self.last_sync)

    def describe_last_sync(self) -> str:
        age = self.last_sync_age
        if age is None:
            return "Never"
        if age < 5:
            return "Just now"
        if age < 60:
            return f"{int(age)}s ago"
        if age < 3600:
            return f"{int(age // 60)}m ago"
        return f"{int(age // 3600)}h ago"
