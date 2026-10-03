"""Application state.

Every reactive value the app shares lives here as a named
:class:`~pydrud.State`. States survive navigation and (for the framework's
stateful hot reload) module reloads, which is exactly what a preview
companion needs: connection bookkeeping must outlive any one screen.

Screen-local state stays local; anything two screens need to agree on
belongs in this module.
"""

from __future__ import annotations

from pydrud import State

#: ── Shell ───────────────────────────────────────────────────────────────────
#: Which of the four main destinations is showing (0=Home, 1=Components,
#: 2=Playground, 3=Settings).
active_tab = State(0, name="active_tab")

#: Preferred appearance: "system" | "light" | "dark".
theme_mode = State("system", name="theme_mode")

#: The user's brand seed colour (applied via Theme.seed).
brand_seed = State("", name="brand_seed")

#: ── Settings ────────────────────────────────────────────────────────────────
#: Try to re-establish a dropped preview session automatically.
auto_reconnect = State(True, name="auto_reconnect")
#: Fire haptic ticks on connection milestones and preview errors.
haptics_enabled = State(True, name="haptics_enabled")
#: Keep the screen awake while a preview session is live.
keep_awake = State(False, name="keep_awake")

#: ── Connection flow ─────────────────────────────────────────────────────────
#: The last connection payload the user scanned or typed, kept so the Home
#: screen can offer "Reconnect" after the server goes away.
last_endpoint = State(None, name="last_endpoint")

#: Monotonic tick bumped whenever the preview session changes state, so
#: screens can simply read it during rebuilds.
session_pulse = State(0, name="session_pulse")

#: Component showcase: active search filter ("" shows everything).
catalog_query = State("", name="catalog_query")

#: Component showcase: chips the user toggled on.
catalog_filters = State((), name="catalog_filters")


def bump(*_args) -> None:
    """Nudge :data:`session_pulse` so open screens re-read session state."""
    session_pulse.value += 1


__all__ = [
    "active_tab", "auto_reconnect", "brand_seed", "bump", "catalog_filters",
    "catalog_query", "haptics_enabled", "keep_awake", "last_endpoint",
    "session_pulse", "theme_mode",
]
