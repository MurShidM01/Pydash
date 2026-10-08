"""Application state.

Every reactive value the app shares lives here as a named
:class:`~pydrud.State`. States survive navigation and (for the framework's
stateful hot reload) module reloads — exactly what a preview companion needs:
connection bookkeeping must outlive any one screen.

Screen-local state stays local; anything two screens need to agree on belongs
in this module.
"""

from __future__ import annotations

from pydrud import State

# ── Shell ────────────────────────────────────────────────────────────────────
#: Which of the two main destinations is showing (0=Home, 1=Settings).
active_tab = State(0, name="active_tab")

#: Preferred appearance: "system" | "light" | "dark".
theme_mode = State("system", name="theme_mode")

# ── Settings ─────────────────────────────────────────────────────────────────
#: Try to re-establish a dropped preview session automatically.
auto_reconnect = State(True, name="auto_reconnect")
#: Fire haptic ticks on connection milestones and preview errors.
haptics_enabled = State(True, name="haptics_enabled")
#: Keep the screen awake while a preview session is live.
keep_awake = State(False, name="keep_awake")

# ── Connection flow ──────────────────────────────────────────────────────────
#: The last connection payload the user scanned or typed, kept so Home can
#: offer "Reconnect" after the server goes away.
last_endpoint = State(None, name="last_endpoint")

#: The recent-apps list: endpoint payloads (plus ``last_used``), newest first.
#: Owned by :mod:`app.recents`, which also persists it.
recents = State([], name="recents")

#: True while a connection attempt the user started is in flight. Screens use
#: it to show a spinner instead of a stale button.
connecting = State(False, name="connecting")

#: The endpoint being connected (a payload dict), so a specific recent row can
#: show its own spinner. ``None`` when nothing is pending.
connecting_endpoint = State(None, name="connecting_endpoint")

#: Which screen started the pending connection: ``"scan"`` or ``"home"``. The
#: resolver navigates differently for each when the link comes up.
connecting_origin = State("", name="connecting_origin")

#: A message for the "app is not responding" dialog, or ``None`` when there is
#: nothing to report. Set when a connection the user expected to work fails.
connection_failed = State(None, name="connection_failed")

#: Monotonic tick bumped whenever the preview session changes state, so screens
#: can simply read it during rebuilds.
session_pulse = State(0, name="session_pulse")


def bump(*_args) -> None:
    """Nudge :data:`session_pulse` so open screens re-read session state."""
    session_pulse.value += 1


__all__ = [
    "active_tab", "auto_reconnect", "bump", "connecting",
    "connecting_endpoint", "connecting_origin", "connection_failed",
    "haptics_enabled", "keep_awake", "last_endpoint", "recents",
    "session_pulse", "theme_mode",
]
