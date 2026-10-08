"""The recent-apps list — the last few projects, with a 15-minute expiry.

A *recent* is an :class:`~app.preview.models.Endpoint` plus the wall-clock
time it was last used. Entries older than :data:`TTL_SECONDS` are dropped,
because the one-run token printed by ``pydrud dev`` only lives as long as that
run — a stale entry could not reconnect anyway, so keeping it would only offer
the user a button that cannot work.

The list is persisted through :mod:`app.storage`, so it survives a relaunch,
and it is re-pruned on a timer while the app is open so a stale row disappears
on its own instead of waiting for the next cold start.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from app import state, storage
from app.preview.models import Endpoint
from app.runtime import refresh

__all__ = [
    "MAX_ENTRIES", "TTL_SECONDS", "age_label", "clear", "entries", "forget",
    "load", "prune", "remember", "touch",
]

#: How long an unused entry stays in the list.
TTL_SECONDS = 15 * 60
#: The list is a shortcut, not a history — a handful is plenty.
MAX_ENTRIES = 5
#: How often the open app re-checks for expired entries.
_PRUNE_INTERVAL = 30.0

_loaded = False
_pruning = False


# ── reads ────────────────────────────────────────────────────────────────────


def entries() -> list:
    """The live recent list (a copy), newest first."""
    value = state.recents.value
    return list(value) if isinstance(value, list) else []


def age_label(entry: dict, *, now: Optional[float] = None) -> str:
    """A short "5m ago" style label for a recent entry."""
    now = time.time() if now is None else now
    used = _last_used(entry)
    if used is None:
        return ""
    age = max(0.0, now - used)
    if age < 60:
        return "just now"
    if age < 3600:
        return f"{int(age // 60)}m ago"
    return f"{int(age // 3600)}h ago"


# ── writes ───────────────────────────────────────────────────────────────────


def remember(endpoint: Endpoint) -> None:
    """Add (or refresh) an endpoint at the top of the list, then persist."""
    entry = {**endpoint.as_dict(), "last_used": time.time()}
    identity = _identity(entry)
    kept = [e for e in entries() if _identity(e) != identity]
    state.recents.value = ([entry] + kept)[:MAX_ENTRIES]
    _persist()


#: A recents tap re-checks the link; that is the same "recently used" moment.
touch = remember


def forget(endpoint: Endpoint) -> None:
    identity = _identity(endpoint.as_dict())
    state.recents.value = [e for e in entries() if _identity(e) != identity]
    _persist()


def clear() -> None:
    state.recents.value = []
    _persist()


def prune(*, now: Optional[float] = None) -> bool:
    """Drop expired entries. Returns ``True`` when the list changed."""
    now = time.time() if now is None else now
    current = entries()
    kept = [e for e in current if _fresh(e, now)]
    if len(kept) == len(current):
        return False
    state.recents.value = kept
    return True


# ── persistence ──────────────────────────────────────────────────────────────


def load(page) -> None:
    """Read the stored list once, dropping anything already expired."""
    global _loaded
    if _loaded or page is None:
        return
    if not storage.ready(page):
        return
    _loaded = True
    storage.read(page, "recents", [], apply=_on_loaded)
    _start_expiry()


def _on_loaded(value: Any) -> None:
    items = value if isinstance(value, list) else []
    now = time.time()
    fresh = [e for e in items if isinstance(e, dict) and _fresh(e, now)]
    state.recents.value = fresh[:MAX_ENTRIES]
    if len(fresh) != len(items):
        _persist()
    refresh()


def _persist() -> None:
    page = _page()
    if page is not None:
        storage.write(page, "recents", entries())


# ── expiry timer ─────────────────────────────────────────────────────────────


def _start_expiry() -> None:
    """Re-check for expired entries on a timer while the app runs."""
    global _pruning
    if _pruning:
        return
    _pruning = True
    _schedule_expiry()


def _schedule_expiry() -> None:
    from app.runtime import after

    after(_PRUNE_INTERVAL, _expire_tick)


def _expire_tick() -> None:
    if prune():
        _persist()
        refresh()
    _schedule_expiry()


# ── helpers ──────────────────────────────────────────────────────────────────


def _fresh(entry: dict, now: float) -> bool:
    if not isinstance(entry, dict):
        return False
    used = _last_used(entry)
    if used is None:
        return False
    return (now - used) <= TTL_SECONDS


def _last_used(entry: dict) -> Optional[float]:
    try:
        return float(entry.get("last_used"))
    except (TypeError, ValueError):
        return None


def _identity(entry: dict) -> tuple:
    try:
        port = int(entry.get("port", 0) or 0)
    except (TypeError, ValueError):
        port = 0
    return (str(entry.get("host", "")), port, str(entry.get("project_id", "")))


def _page():
    from app.runtime import current

    app = current()
    return app.page if app is not None else None
