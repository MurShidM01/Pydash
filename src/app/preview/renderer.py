"""Renders the mirrored remote tree and handles commands from the dev server.

The preview screen delegates here. Two responsibilities:

* :func:`build_preview_body` rehydrates the mirrored JSON into
  :class:`~app.preview.mirror.MirrorWidget` nodes, so the *real* Pydrud renderer
  draws the remote project's UI natively;
* :func:`handle_remote_command` applies everything the server sends that is not
  a render transaction — theme pushes, toasts, dialogs, native service calls,
  back results — and forwards widget events back over the socket.
"""

from __future__ import annotations

from typing import Any

from pydrud import Column, Container, Row, Text, Theme, Tokens

from app.preview.mirror import MirrorWidget, remote_key
from app.preview.models import ConnectionState, STATE_HINTS, STATE_LABELS
from app.preview.session import session
from app.runtime import current, on_ui, refresh
from app import theme as design

__all__ = [
    "adopt_remote_theme", "build_preview_body", "forward_event", "handle_back",
    "handle_metrics", "handle_remote_command", "preview_header",
    "release_remote_theme",
]

#: Server commands that make sense on the client's own native layer verbatim.
_PASS_THROUGH = frozenset({
    "toast", "snackbar", "set_title", "set_system_ui", "theme_mode",
    "orientation", "fullscreen", "keep_awake", "focus", "keyboard",
    "scroll_to", "drawer", "end_refresh", "vibrate", "route_transition",
})

#: Commands the client understands but does not replay locally.
_IGNORED = frozenset({"navigate", "back"})

#: Pydash's own look, saved before the first remote theme push.
_SAVED_LOOK: dict = {}

#: The most recent palette the dev server sent. Kept so the preview can adopt
#: it the moment the screen is shown — the server pushes its theme during the
#: handshake, which happens while the *scan* screen is still up, so applying it
#: eagerly would re-theme the wrong screen.
_REMOTE_THEME: dict = {}

#: Whether the cached palette is already on the native layer. The preview
#: screen is rebuilt on every render transaction (up to once a frame while an
#: animation runs), so re-applying the theme each time would be pure overhead.
_adopted = False


# ── building the preview ─────────────────────────────────────────────────────


def build_preview_body():
    """The previewed project's UI, or a state surface while it is unavailable."""
    if session.tree.is_empty:
        return _state_surface()
    node = session.tree.snapshot_json()
    if not node:
        return _state_surface()
    return Container(
        key="pd_stage",
        expand=1,
        width="match",
        height="match",
        child=MirrorWidget(node, on_event=forward_event),
    )


def preview_header():
    """A compact client bar shown above the stage when not immersive."""
    from app.components import status_pill

    project = session.project_name
    return Row(
        key="pd_preview_bar",
        spacing=12,
        vertical_alignment="center",
        main_axis_size="max",
        children=[
            Container(
                key="pd_preview_icon",
                class_="pd-icon-badge",
                child=Text("▶", key="pd_preview_icon_t", size=16,
                           color=Theme.primary),
            ),
            Column(key="pd_preview_titles", spacing=2, expand=1, children=[
                Text(project, key="pd_preview_title", class_="pd-h2",
                     max_lines=1, overflow="ellipsis"),
                Text(session.endpoint.describe() if session.endpoint else "",
                     key="pd_preview_sub", class_="pd-body", max_lines=1,
                     overflow="ellipsis"),
            ]),
            status_pill(),
        ],
    )


def _state_surface():
    """A centred notice for the connecting / failed / idle states."""
    state = session.state
    label = STATE_LABELS.get(state, "Preview")
    hint = session.describe_error() or STATE_HINTS.get(state, "")
    busy = state in (ConnectionState.CONNECTING, ConnectionState.HANDSHAKING,
                     ConnectionState.RECONNECTING, ConnectionState.SYNCING)
    return Container(
        key="pd_stage_state",
        expand=1,
        width="match",
        height="match",
        alignment="center",
        padding=design.insets(horizontal=32),
        child=Column(key="pd_stage_inner", spacing=10, children=[
            Container(
                key="pd_stage_dot",
                class_="pd-dot",
                style={"width": 44, "height": 44, "borderRadius": 999,
                       "bg": design.status_surface(state)},
            ),
            Text(label, key="pd_stage_label", class_="pd-h2", text_align="center"),
            Text(hint or "Waiting…", key="pd_stage_hint", class_="pd-body",
                 text_align="center"),
            Text("Connecting…" if busy else "", key="pd_stage_busy",
                 class_="pd-caption"),
        ]),
    )


# ── events (client → server) ─────────────────────────────────────────────────


def forward_event(event_name: str, event: Any) -> None:
    """Relay one widget event from the local renderer back to the server."""
    client = session.client
    if client is None:
        return
    # The local renderer reports the *namespaced* key; the dev server
    # dispatches by the project's own key, so strip the prefix back off.
    key = remote_key(getattr(event, "key", "") or "")
    value = None
    try:
        value = event.value
    except Exception:
        value = None
    client.send_event(key, event_name, value)
    session.stats.events_sent += 1


def handle_back() -> bool:
    """Offer the hardware back press to the remote project first."""
    client = session.client
    if client is None or not session.is_live:
        return False
    client.send_back()
    return True


def handle_metrics() -> None:
    """Tell the dev server the window changed (rotation, keyboard, foldables)."""
    client = session.client
    if client is None:
        return
    from app.preview.session import _current_metrics
    client.send_metrics(_current_metrics())


# ── commands (server → client) ───────────────────────────────────────────────


def handle_remote_command(message: dict) -> None:
    """Apply one command from the development server."""
    cmd = message.get("cmd")
    if not cmd:
        return
    fields = {key: value for key, value in message.items() if key != "cmd"}

    if cmd == "theme":
        _REMOTE_THEME.clear()
        _REMOTE_THEME.update(fields)
        on_ui(_refresh_remote_theme)
        return
    if cmd == "set_title":
        session.remote_title = str(fields.get("title") or "")
        on_ui(refresh)
        return
    if cmd == "back_result":
        _handle_back_result(fields)
        return
    if cmd == "finish_activity":
        on_ui(_leave_preview)
        return
    if cmd in _IGNORED:
        return
    if "id" in fields:
        _run_remote_service(cmd, fields)
        return
    if cmd in _PASS_THROUGH:
        on_ui(_pass_through, cmd, fields)
        return
    # Unknown command: forward it so the native layer can decide.
    on_ui(_pass_through, cmd, fields)


def _pass_through(cmd: str, fields: dict) -> None:
    app = current()
    page = app.page if app is not None else None
    if page is None:
        return
    try:
        # ``scroll_to`` / ``focus`` address a widget by the project's key; the
        # native view map is keyed by the namespaced mirror key.
        page._send(cmd, **{k: (remote_key(v) if k == "key" else v)
                           for k, v in fields.items()})  # noqa: SLF001
    except Exception:
        pass


def _run_remote_service(cmd: str, fields: dict) -> None:
    """Answer a service command that carried a request ``id``."""
    request_id = fields.pop("id", None)

    def run():
        app = current()
        page = app.page if app is not None else None
        if page is None:
            _send_result(request_id, False, error="no renderer")
            return
        try:
            result = page.invoke(cmd, **fields)
        except Exception as exc:
            _send_result(request_id, False, error=str(exc))
            return
        try:
            result.then(lambda value: _send_result(request_id, True, value=value))
            result.catch(lambda err: _send_result(request_id, False, error=str(err)))
        except Exception as exc:
            _send_result(request_id, False, error=str(exc))

    on_ui(run)


def _send_result(request_id: Any, ok: bool, *, value: Any = None,
                 error: Any = None) -> None:
    client = session.client
    if client is None:
        return
    client.send_result(request_id, ok, value=value, error=error)


def _handle_back_result(fields: dict) -> None:
    handled = bool(fields.get("handled"))

    def act():
        if not handled:
            _leave_preview()

    on_ui(act)


def _leave_preview() -> None:
    """Return to the dashboard when the remote has nothing left to pop."""
    from app.runtime import router

    try:
        if router.current_route == "preview":
            router.pop()
    except Exception:
        pass


# ── theme custody ────────────────────────────────────────────────────────────


def _remember_pydash_look() -> None:
    if _SAVED_LOOK:
        return
    _SAVED_LOOK["roles"] = {
        name: getattr(Theme, name) for name in Theme._ROLES  # noqa: SLF001
    }
    _SAVED_LOOK["dark"] = bool(Theme.dark_mode)
    _SAVED_LOOK["tokens"] = Tokens.as_dict()


def _restore_pydash_look() -> None:
    """Return the client to its own palette after a preview session ends."""
    if not _SAVED_LOOK:
        return
    Theme.configure(dark_mode=_SAVED_LOOK.get("dark", False),
                    **_SAVED_LOOK.get("roles", {}))
    Theme.scheme = None
    saved_tokens = _SAVED_LOOK.get("tokens")
    if saved_tokens:
        Tokens.reset()
        Tokens.update(**saved_tokens)
    app = current()
    if app is not None:
        app.apply_theme()


def _apply_remote_theme(payload: dict) -> None:
    """Adopt the previewed project's palette on the native layer."""
    global _adopted
    _remember_pydash_look()
    roles = {
        "primary": "primary", "background": "background", "surface": "surface",
        "on_surface": "text", "secondary": "secondary",
        "surface_variant": "surface_variant", "outline": "outline",
        "error": "error", "on_primary": "on_primary",
        "on_surface_variant": "text_secondary",
    }
    overrides: dict = {}
    for source, target in roles.items():
        value = payload.get(source)
        if isinstance(value, str) and value:
            overrides[target] = value
    if "dark" in payload:
        overrides["dark_mode"] = bool(payload.get("dark"))
    Theme.configure(**overrides)
    Theme.scheme = None
    tokens = payload.get("tokens")
    if isinstance(tokens, dict):
        known = set(Tokens.names())
        valid = {name: value for name, value in tokens.items() if name in known}
        if valid:
            Tokens.update(**valid)
    app = current()
    if app is not None:
        app.apply_theme()
    _adopted = True
    session.theme_applied_by_remote = True


def adopt_remote_theme() -> None:
    """Put the previewed project's palette on screen (called on entry).

    The dev server pushes its theme during the handshake, while the scan
    screen is still showing, so it is cached rather than applied immediately.
    Entering the preview adopts it; leaving restores Pydash's own look. The
    preview screen rebuilds on every render transaction, so this is guarded to
    run once per entry — re-theming the native layer each frame would be
    wasteful and can fight the render loop.
    """
    if _adopted or not _REMOTE_THEME:
        return
    _apply_remote_theme(dict(_REMOTE_THEME))


def release_remote_theme() -> None:
    """Return Pydash to its own palette after the preview is left."""
    global _adopted
    _adopted = False
    _restore_pydash_look()


def _refresh_remote_theme() -> None:
    """Apply the cached palette, but only while the preview is on screen."""
    from app.runtime import router

    if router.current_route == "preview" and _REMOTE_THEME:
        _apply_remote_theme(dict(_REMOTE_THEME))


def _forget_remote_theme() -> None:
    """Drop the cached palette when a session ends, so a later project never
    inherits the previous one's colours before its own theme arrives."""
    global _adopted
    _REMOTE_THEME.clear()
    _adopted = False


def _install_theme_custody() -> None:
    if _restore_pydash_look not in session.on_disconnect_hooks:
        session.on_disconnect_hooks.append(_restore_pydash_look)
    if _forget_remote_theme not in session.on_disconnect_hooks:
        session.on_disconnect_hooks.append(_forget_remote_theme)


_install_theme_custody()
