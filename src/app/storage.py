"""Persistence plumbing shared by Pydash's settings and its recent-apps list.

Everything durable rides on Pydrud's ``storage`` service (Android
``SharedPreferences``). Two facts about that service shape this module:

* **The bridge is not connected during the first tree build.** ``App.run``
  builds the tree and only then connects to the native renderer, so a read
  issued from the first build is answered with "bridge not connected" and is
  lost. :func:`ready` lets a caller wait, and :func:`read` reports whether it
  could issue the call so the caller can retry on the next build.
* **The answer arrives on the bridge's reader thread.** Every callback is
  marshalled onto the UI thread through :func:`app.runtime.on_ui` before it
  touches a reactive ``State`` or the theme, exactly like the preview session
  does with its own socket callbacks.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

__all__ = ["KEY_PREFIX", "read", "write", "remove", "ready"]

#: Every key Pydash owns is namespaced, so a stored value is recognisably ours.
KEY_PREFIX = "pd_"


def ready(page) -> bool:
    """Whether the native bridge can answer a storage call right now.

    The first build runs before the renderer connects, so a screen that reads
    storage on its first pass would always fail. Callers gate on this and try
    again on a later build.
    """
    from app.runtime import current

    app = current()
    return app is not None and bool(getattr(app, "connected", False))


def read(
    page,
    key: str,
    default: Any = None,
    *,
    apply: Optional[Callable[[Any], None]] = None,
) -> bool:
    """Read one stored value.

    *apply* runs on the UI thread with the decoded value when the answer
    arrives. Returns ``False`` when the bridge is not up yet (the caller should
    retry), ``True`` once the read has been issued.
    """
    storage = getattr(page, "storage", None)
    if storage is None or not ready(page):
        return False
    try:
        result = storage.get(f"{KEY_PREFIX}{key}", default)
    except Exception:
        return False
    if result.done and result.error:
        return False
    if apply is not None:
        from app.runtime import on_ui

        result.then(lambda value: on_ui(apply, value))
    return True


def write(page, key: str, value: Any) -> bool:
    """Persist one value. Returns ``False`` when nothing could be written."""
    storage = getattr(page, "storage", None)
    if storage is None or not ready(page):
        return False
    try:
        result = storage.set(f"{KEY_PREFIX}{key}", value)
    except Exception:
        return False
    return not (result.done and result.error)


def remove(page, key: str) -> bool:
    """Delete one stored value. Returns ``False`` when nothing was removed."""
    storage = getattr(page, "storage", None)
    if storage is None or not ready(page):
        return False
    try:
        result = storage.remove(f"{KEY_PREFIX}{key}")
    except Exception:
        return False
    return not (result.done and result.error)
