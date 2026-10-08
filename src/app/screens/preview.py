"""Preview — the connected project, rendered natively inside Pydash.

This is the payoff screen. It does almost nothing itself: the mirrored remote
tree is rehydrated by :func:`app.preview.renderer.build_preview_body` and drawn
by Pydrud's own renderer, so the preview is the *real* UI — the project's own
app bars, navigation and all — not a mock. Pydash adds only a thin bar above it
(project identity, connection state, a way out) and hands the hardware back
button to the remote project first.

Entering the screen adopts the previewed project's palette so it looks the way
it would as a real app; leaving restores Pydash's own look. The session is
intentionally *not* torn down when the screen closes — closing returns to the
dashboard with the connection still live, so it can be reopened without
re-scanning. ``Exit session`` is the explicit teardown.
"""

from __future__ import annotations

from pydrud import Column, Container, Icons, Row, Scaffold

from app import connection, theme
from app.components import bar_action
from app.preview.renderer import (
    build_preview_body,
    handle_back,
    handle_metrics,
    preview_header,
    release_remote_theme,
)
from app.preview.session import session
from app.runtime import current, refresh, router

__all__ = ["preview_screen"]

#: Whether the window-metrics hook has been attached to the running app.
_metrics_hooked = False


def preview_screen(page) -> None:
    """Route builder: the immersive preview.

    The previewed palette is adopted *before* this route is built (see
    ``app.preview.renderer.adopt_remote_theme`` and its callers in
    ``connection``, ``home`` and ``main``). Adopting it here — mid-build —
    would nest a full re-render inside the build in progress, which cleared and
    repopulated the page and then appended a second copy of this route's
    widgets (``Duplicate Pydrud widget key 'pd_preview'``), blanking the
    preview the moment it opened.
    """
    router.preview_back_handler = handle_back
    _hook_metrics()
    page.add(Scaffold(
        key="pd_preview",
        class_="pd-screen",
        bg_color=theme.background(),
        body=Column(
            key="pd_preview_body",
            expand=1,
            children=[_bar(), build_preview_body()],
        ),
    ))
    dialog = connection.failure_dialog()
    if dialog is not None:
        page.add_floating(dialog)


# ── the bar ──────────────────────────────────────────────────────────────────


def _bar() -> Container:
    # The bar floats on the previewed project's own background rather than
    # Pydash's surface colour: once the remote palette is adopted (see
    # ``renderer.adopt_remote_theme``), ``theme.background()`` is the project's
    # background, so the chrome blends into the mirrored app instead of
    # framing it in a foreign colour.
    return Container(
        key="pd_preview_bar_wrap",
        width="match",
        padding=theme.insets(left=16, right=8, top=6, bottom=6),
        style={"bg": theme.background()},
        child=Row(
            key="pd_preview_bar_row",
            spacing=6,
            main_axis_size="max",
            vertical_alignment="center",
            children=[
                Container(key="pd_preview_header_slot", expand=1,
                          child=preview_header()),
                bar_action(Icons.LOGOUT, "Exit session", _disconnect,
                           key="pd_preview_exit"),
                bar_action(Icons.CLOSE, "Close preview", _close,
                           key="pd_preview_close"),
            ],
        ),
    )


# ── actions ──────────────────────────────────────────────────────────────────


def _close() -> None:
    """Leave the preview but keep the session alive."""
    _leave()


def _disconnect() -> None:
    """Close the session and return to the dashboard."""
    session.disconnect()
    _leave()


def _leave() -> None:
    """Return to the dashboard however the preview was reached.

    A preview opened from a deep link or a scan *replaces* the previous screen,
    so the router stack can hold the preview as its only entry — and ``pop()``
    on a one-entry stack is a no-op, which is exactly how the exit and close
    buttons appeared to "stop working". Resetting to the shell is deterministic
    from any entry point.
    """
    release_remote_theme()
    try:
        router.reset("shell")
    except Exception:
        router.pop()
    refresh()


# ── metrics ──────────────────────────────────────────────────────────────────


def _hook_metrics() -> None:
    """Tell the dev server when the window changes (rotation, keyboard)."""
    global _metrics_hooked
    if _metrics_hooked:
        return
    app = current()
    if app is None:
        return
    try:
        app.on_metrics_change(lambda _info: handle_metrics())
        _metrics_hooked = True
    except Exception:
        pass
