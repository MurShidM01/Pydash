"""Preference persistence for Pydash's own settings.

Pydash remembers the handful of choices a user makes in Settings — the theme
mode, auto-reconnect, haptics and keep-awake — so the app opens the way it was
left. Persistence rides on Pydrud's ``storage`` service (Android
``SharedPreferences``), through :mod:`app.storage`.

The first tree build runs *before* the native bridge connects, so
:func:`load` only issues its reads once the link is up and otherwise leaves
``_loaded`` clear so the next build tries again. Values land on the UI thread
and rebuild the screen, so a restored theme is visible immediately.
"""

from __future__ import annotations

from typing import Any

from app import state, storage
from app.runtime import refresh

__all__ = ["load", "save"]

#: The settings that persist, each with the reactive state it drives and the
#: default used when nothing has been stored yet.
_FIELDS = {
    "theme_mode": (state.theme_mode, "system"),
    "auto_reconnect": (state.auto_reconnect, True),
    "haptics_enabled": (state.haptics_enabled, True),
    "keep_awake": (state.keep_awake, False),
}

_loaded = False


def load(page) -> None:
    """Read saved preferences into the reactive states (once per process).

    Called from the shell on every build; the first build runs before the
    bridge is connected, so the read is deferred until the link can answer.
    """
    global _loaded
    if _loaded or page is None:
        return
    if not storage.ready(page):
        return
    _loaded = True
    for name, (target, default) in _FIELDS.items():
        storage.read(page, name, default, apply=_applier(name, target, page))


def save(**values: Any) -> None:
    """Persist one or more changed settings (fire-and-forget)."""
    page = _page()
    if page is None:
        return
    for name, value in values.items():
        if name in _FIELDS:
            storage.write(page, name, value)


def _applier(name: str, target, page):
    """Build the UI-thread callback that adopts one stored setting."""

    def apply(value: Any) -> None:
        if value is None:
            return
        try:
            target.value = value
        except Exception:
            return
        if name == "keep_awake":
            _apply_keep_awake(page, bool(value))
        elif name == "theme_mode":
            from app import theme

            try:
                theme.apply_theme_mode(page, str(value))
            except Exception:
                pass
        refresh()

    return apply


def _apply_keep_awake(page, enabled: bool) -> None:
    try:
        page.keep_awake(bool(enabled))
    except Exception:
        pass


def _page():
    from app.runtime import current

    app = current()
    return app.page if app is not None else None
