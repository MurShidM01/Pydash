"""Render the previewed project inside Pydash and bridge its commands.

The renderer is the client half of the display pipeline:

* :func:`build_preview_body` turns the mirrored JSON tree into live
  :class:`~app.preview.mirror.MirrorWidget` widgets, so the local Pydrud
  renderer draws the project's UI natively — a previewed ``Button`` is a
  real Material button;
* :func:`handle_remote_command` executes the page commands the previewed
  project emits (toasts, snackbars, dialogs, theme pushes, …) on this
  device, which is what makes the preview behave like the real app;
* :func:`forward_event` relays taps and value changes from the previewed
  widgets back to the developer's Python;
* the service bridge runs native calls the previewed project requests
  (dialogs, storage, haptics, …) locally and answers with ``result``
  frames, keeping the phone responsible for device features while the
  developer machine stays responsible for the app logic.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from pydrud import (
    Colors, Column, Container, Divider, Icon, Icons, Padding, Row,
    SizedBox, Skeleton, Spacing, Text, Widget,
)
from pydrud.core.responsive import MediaQuery

from app.preview.mirror import MirrorWidget
from app.preview.models import ConnectionState
from app.preview.session import session
from app.runtime import current, on_ui, refresh, router
from app.state import bump, keep_awake, theme_mode
from app.theme import code_style, pad, status_color

__all__ = [
    "build_preview_body", "forward_event", "handle_back", "handle_metrics",
    "handle_remote_command", "preview_header",
]


# ── preview body ────────────────────────────────────────────────────────────

def build_preview_body() -> Widget:
    """The remote project's page — or the state surface explaining why
    it cannot be shown yet."""
    state = session.state

    if state in (ConnectionState.CONNECTING, ConnectionState.HANDSHAKING,
                 ConnectionState.RECONNECTING):
        return _handshake_surface(state)

    if state == ConnectionState.FAILED:
        return _failure_surface()

    if session.tree.is_empty:
        return _awaiting_snapshot_surface()

    node = session.tree.snapshot_json()
    if node is None:
        return _awaiting_snapshot_surface()
    return Container(
        key="pd_preview_host",
        width="match",
        height="match",
        child=MirrorWidget(node, on_event=forward_event),
    )


def _handshake_surface(state: str) -> Widget:
    detail = {
        ConnectionState.CONNECTING: "Reaching the development server…",
        ConnectionState.HANDSHAKING: "Negotiating the preview session…",
        ConnectionState.RECONNECTING:
            f"Reconnecting (attempt {session.reconnect_attempt})…",
    }.get(state, "Connecting…")
    return _centered_notice(
        key="pd_preview_connecting", icon=Icons.SYNC, title="Connecting",
        detail=detail, tone="pending", progress=True)


def _awaiting_snapshot_surface() -> Widget:
    return Column(
        key="pd_preview_waiting",
        spacing=Spacing.MD,
        horizontal_alignment="center",
        vertical_alignment="center",
        expand=1,
        children=[
            Text("Waiting for the first UI snapshot",
                 key="pd_preview_wait_title", size=15, weight=600,
                 color=Colors.WHITE),
            Skeleton(key="pd_preview_skel1", width="match", height=18),
            Skeleton(key="pd_preview_skel2", width="match", height=18),
            Skeleton(key="pd_preview_skel3", width="60%", height=18),
        ],
    )


def _failure_surface() -> Widget:
    return _centered_notice(
        key="pd_preview_failed", icon=Icons.WARNING,
        title="Preview unavailable",
        detail=session.describe_error() or
               "The development server could not be reached.",
        tone="error")


def _centered_notice(*, key: str, icon: str, title: str, detail: str,
                     tone: str, progress: bool = False) -> Widget:
    from pydrud import CircularProgress

    accent = Colors.WHITE
    children: list[Widget] = [
        Icon(icon, key=f"{key}_icon", size=30, color=accent),
        Text(title, key=f"{key}_title", size=17, weight=700, color=accent),
        Text(detail, key=f"{key}_detail", size=13,
             color=Colors.with_opacity(Colors.WHITE, 0.8),
             text_align="center"),
    ]
    if progress:
        children.append(SizedBox(key=f"{key}_gap", height=Spacing.SM))
        children.append(CircularProgress(key=f"{key}_spin", size=26,
                                         stroke=3, color=accent))
    return Column(
        key=key,
        spacing=Spacing.SM,
        horizontal_alignment="center",
        vertical_alignment="center",
        expand=1,
        children=children,
    )


# ── preview chrome ──────────────────────────────────────────────────────────

def preview_header() -> Widget:
    """The slim client chrome pinned above the previewed UI."""
    from app.components.status import StatusDot

    revision = f"rev {session.stats.revision}" if session.stats.revision else "syncing…"
    title = session.remote_title or session.project_name
    return Container(
        key="pd_preview_header",
        width="match",
        bg=Colors.with_opacity(Colors.BLACK, 0.55),
        padding=pad(horizontal=Spacing.MD, vertical=Spacing.XS),
        child=Row(
            key="pd_preview_header_row",
            vertical_alignment="center",
            spacing=Spacing.SM,
            children=[
                Icon(Icons.CHEVRON_LEFT, key="pd_preview_back", size=20,
                     color=Colors.WHITE).on_click(lambda _e: exit_preview()),
                StatusDot(key="pd_preview_dot", state=session.state),
                Text(title, key="pd_preview_title", size=14, weight=600,
                     color=Colors.WHITE, expand=1, max_lines=1,
                     overflow="ellipsis"),
                Text(revision, key="pd_preview_rev", size=11,
                     color=Colors.with_opacity(Colors.WHITE, 0.75)),
                SizedBox(key="pd_preview_hgap", width=Spacing.XS),
                Icon(Icons.CLOSE, key="pd_preview_disconnect", size=18,
                     color=Colors.with_opacity(Colors.WHITE, 0.85)
                     ).on_click(lambda _e: exit_preview()),
            ],
        ),
    )


def exit_preview() -> None:
    """Leave the preview screen; drop the session on the way out."""
    global _back_offered_at
    from app.state import active_tab

    _back_offered_at = None
    if session.is_live or session.is_busy:
        session.disconnect(reason="closed from the preview screen")
    _restore_pydash_look()
    active_tab.value = 0
    router.reset("shell")


def sync_pill() -> Widget:
    """A tiny 'last sync' readout for the preview footer."""
    return Row(
        key="pd_sync_pill",
        spacing=Spacing.XS,
        vertical_alignment="center",
        children=[
            Icon(Icons.SYNC, key="pd_sync_icon", size=13,
                 color=Colors.with_opacity(Colors.WHITE, 0.8)),
            Text(session.stats.describe_last_sync(), key="pd_sync_label",
                 size=11, color=Colors.with_opacity(Colors.WHITE, 0.8)),
        ],
    )


# ── event forwarding (previewed widgets → dev server) ──────────────────────

def forward_event(kind: str, event: Any) -> None:
    """Relay a tap/change/submit from the previewed UI to the server."""
    client = session.client
    if client is None or not client.is_connected:
        return
    data = dict(getattr(event, "data", None) or {})
    client.send_event(str(kind), str(getattr(event, "key", "")), data)


#: How long a back offer may stay unanswered before the next press exits.
_BACK_ANSWER_WINDOW = 1.5

#: When the current back offer was sent (``time.time()``), if unanswered.
_back_offered_at: Optional[float] = None


def handle_back() -> None:
    """Offer a hardware back press to the previewed project first.

    The project answers asynchronously with a ``back_result`` command:
    handled (it popped its own navigation stack) or not handled (Pydash
    leaves the preview). If the answer never comes — the dev server sits
    on a breakpoint, a handler hangs — the user must still be able to
    leave the immersive preview, so a second press after
    :data:`_BACK_ANSWER_WINDOW` seconds exits outright.
    """
    global _back_offered_at
    client = session.client
    if client is not None and client.is_connected:
        now = time.time()
        if (_back_offered_at is not None
                and now - _back_offered_at > _BACK_ANSWER_WINDOW):
            _back_offered_at = None
            exit_preview()
            return
        _back_offered_at = now
        client.send_back()
    else:
        exit_preview()


def handle_metrics() -> None:
    """Forward local window changes so the preview reflows correctly."""
    client = session.client
    if client is None or not client.is_connected:
        return
    try:
        client.send_metrics(dict(MediaQuery.info().as_dict()))
    except Exception:
        pass


# ── remote page commands ────────────────────────────────────────────────────

#: Fire-and-forget commands Pydash can safely pass straight to its own
#: native bridge (the previewed project asked for them).
_PASS_THROUGH = (
    "set_system_ui", "drawer", "scroll_to", "focus", "keyboard",
    "end_refresh", "vibrate", "keep_awake", "orientation", "fullscreen",
    "route_transition",
)

#: Commands that re-style the whole client while a session is live.
_LOOK_COMMANDS = ("theme", "theme_mode", "set_system_ui", "orientation",
                  "fullscreen", "keep_awake")


def handle_remote_command(message: dict) -> None:
    """Execute one command emitted by the previewed project.

    Called on the client's reader thread; UI work is marshalled.
    """
    cmd = str(message.get("cmd") or "")
    if not cmd or cmd.startswith("_pydash"):
        if cmd == "_pydash_protocol_error":
            on_ui(lambda: _note_protocol_error(message))
        return

    if "request_id" in message:
        on_ui(lambda: _run_remote_service(message))
        return

    def run():
        _dispatch_page_command(cmd, message)
    on_ui(run)


def _dispatch_page_command(cmd: str, message: dict) -> None:
    global _back_offered_at
    page = _page()
    if page is None:
        return

    if cmd == "theme":
        payload = {k: v for k, v in message.items() if k != "cmd"}
        _remember_pydash_look()
        session.theme_applied_by_remote = True
        page._send("theme", **payload)  # noqa: WPS437 - raw bridge cmd
        return

    if cmd == "theme_mode":
        mode = str(message.get("mode") or "system")
        if mode in ("light", "dark", "system"):
            _remember_pydash_look()
            session.theme_applied_by_remote = True
            page.set_theme_mode(mode)
        return

    if cmd == "toast":
        page.toast(str(message.get("message") or ""),
                   long=bool(message.get("long")))
        return

    if cmd == "snackbar":
        _show_remote_snackbar(page, message)
        return

    if cmd == "set_title":
        session.remote_title = str(message.get("title") or "")
        bump()
        refresh()
        return

    if cmd == "back_result":
        global _back_offered_at
        _back_offered_at = None
        if not message.get("handled"):
            # The project has nothing to pop — leave the preview.
            exit_preview()
        return

    if cmd == "finish_activity":
        # A previewed project cannot close Pydash itself; treat it as an
        # exit request from the preview screen.
        exit_preview()
        return

    if cmd == "navigate":
        # The remote router re-renders through transactions; a navigate
        # command carries no extra work for the client.
        return

    if cmd in _PASS_THROUGH:
        if cmd in _LOOK_COMMANDS:
            _remember_pydash_look()
            session.theme_applied_by_remote = True
        payload = {k: v for k, v in message.items() if k != "cmd"}
        page._send(cmd, **payload)  # noqa: WPS437 - raw bridge cmd


def _show_remote_snackbar(page, message: dict) -> None:
    """Replay the project's snackbar and report the user's choice back."""
    client = session.client
    callback_id = str(message.get("callback_id") or "")

    def report(actioned: bool):
        if client is not None and callback_id:
            client.send_event("snackbar", "", {
                "callback_id": callback_id, "action": actioned})

    page.snack_bar(
        str(message.get("message") or ""),
        action=str(message.get("action") or ""),
        on_action=lambda: report(True),
        on_dismiss=lambda: report(False),
        long=bool(message.get("long", True)),
    )


# ── native service bridge ───────────────────────────────────────────────────

def _run_remote_service(message: dict) -> None:
    """Run a native service call for the previewed project on this device."""
    page = _page()
    client = session.client
    if page is None or client is None:
        return
    request_id = str(message.get("request_id"))
    cmd = str(message.get("cmd"))
    fields = {k: v for k, v in message.items()
              if k not in ("cmd", "request_id")}

    result = page.invoke(cmd, **fields)

    def deliver(value):
        client.send_result(request_id, ok=True, value=value)

    def fail(error):
        client.send_result(request_id, ok=False, error=error)

    result.then(deliver).catch(fail)


# ── look & feel custody ─────────────────────────────────────────────────────

_PYDASH_LOOK: dict = {}


def _remember_pydash_look() -> None:
    """Stash Pydash's own chrome settings once, before previewing."""
    if _PYDASH_LOOK:
        return
    from pydrud import Theme

    _PYDASH_LOOK.update({
        "theme": Theme.payload(),
        "mode": theme_mode.value,
    })


def _restore_pydash_look() -> None:
    """Undo any restyling a previewed project applied to the client."""
    page = _page()
    if page is None or not _PYDASH_LOOK:
        session.theme_applied_by_remote = False
        return
    payload = dict(_PYDASH_LOOK.get("theme") or {})
    mode = str(_PYDASH_LOOK.get("mode") or "system")
    try:
        page._send("theme", **payload)  # noqa: WPS437 - raw bridge cmd
        page._send("set_system_ui",      # noqa: WPS437 - raw bridge cmd
                   status_bar_color=payload.get("primary"),
                   icon_brightness="dark" if payload.get("dark") else "light")
        page._send("orientation", value="auto")  # noqa: WPS437
        page._send("fullscreen", enabled=False)   # noqa: WPS437
        page.set_theme_mode(mode)
    except Exception:
        pass
    if keep_awake.value:
        page.keep_awake(False)
    session.theme_applied_by_remote = False


def _note_protocol_error(message: dict) -> None:
    session.error = str(message.get("message") or "protocol error")
    session.error_code = "protocol"
    bump()
    refresh()


def _page():
    app = current()
    return app.page if app is not None else None


# ── session hooks ───────────────────────────────────────────────────────────

def _on_session_disconnected() -> None:
    if session.theme_applied_by_remote:
        _restore_pydash_look()


session.on_disconnect_hooks.append(_on_session_disconnected)
