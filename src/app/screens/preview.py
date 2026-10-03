"""Preview — the live project host screen.

When a session is live this screen *is* the previewed app: the mirrored
tree renders natively below a slim client header (back, project name,
revision, disconnect). Connecting, reconnecting and failure states get
their own quiet surfaces so the screen always explains itself.

Hardware back is offered to the previewed project first — see
:meth:`app.runtime.PydashRouter.handle_back` — so the project's own
navigation feels real; only when it declines does the user leave.
"""

from __future__ import annotations

from pydrud import (
    Colors, Column, Container, Icon, Icons, Radius, Row, Spacing, Stack,
    Text, Theme, Widget,
)

from app.components.status import StatusDot
from app.preview.models import ConnectionState
from app.preview.renderer import (
    build_preview_body, exit_preview, handle_back, handle_metrics,
    preview_header, sync_pill,
)
from app.preview.session import session
from app.runtime import current, refresh, router
from app.state import keep_awake
from app.theme import pad

__all__ = ["preview_screen"]


def preview_screen(page) -> None:
    """Build the live preview host."""
    page.bgcolor = Theme.background

    live = session.is_live or session.is_busy

    page.add(Stack(
        key="pd_preview",
        style={"width": "match", "height": "match", "bg": Theme.background},
        expand=1,
        children=[
            _content(page),
            *([] if live else []),
        ],
    ))

    router.preview_back_handler = (
        handle_back if live else None)
    _manage_chrome(live)


def _content(page) -> Widget:
    live = session.is_live or session.is_busy
    return Column(
        key="pd_preview_col",
        expand=1,
        style={"width": "match", "height": "match"},
        children=[
            _client_bar(live),
            Container(
                key="pd_preview_stage",
                width="match",
                height="match",
                expand=1,
                bg=Theme.background if not live else Colors.BLACK,
                child=_stage(live),
            ),
            *(_footer() if live else []),
        ],
    )


def _stage(live: bool) -> Widget:
    if not live:
        return _summary_surface()
    return Container(
        key="pd_preview_stage_live",
        width="match",
        height="match",
        child=build_preview_body(),
    )


def _client_bar(live: bool) -> Widget:
    title = (session.remote_title or session.project_name) if live \
        else "Live preview"
    return Container(
        key="pd_preview_bar",
        width="match",
        bg=Theme.primary if not live else Colors.with_opacity(
            Colors.BLACK, 0.72),
        padding=pad(horizontal=Spacing.SM, vertical=Spacing.SM),
        child=Row(
            key="pd_preview_bar_row",
            spacing=Spacing.SM,
            vertical_alignment="center",
            children=[
                Icon(Icons.CHEVRON_LEFT, key="pd_preview_bar_back", size=20,
                     color=Colors.WHITE if live else Theme.on_primary
                     ).on_click(lambda _e: _leave(live)),
                StatusDot("pd_preview_bar_dot", session.state)
                if live else Container(key="pd_preview_bar_dot_off",
                                       width=9, height=9,
                                       border_radius=Radius.PILL,
                                       bg=Theme.on_primary),
                Text(title, key="pd_preview_bar_title", size=14, weight=700,
                     color=Colors.WHITE if live else Theme.on_primary,
                     expand=1, max_lines=1, overflow="ellipsis"),
                Text(f"rev {session.stats.revision}",
                     key="pd_preview_bar_rev", size=11, weight=600,
                     color=Colors.with_opacity(Colors.WHITE, 0.85)
                     if live else Theme.on_primary),
                SizedBox_gap(),
            ],
        ),
    )


def SizedBox_gap() -> Widget:
    from pydrud import SizedBox

    return SizedBox(key="pd_preview_bar_gap", width=Spacing.XS)


def _footer() -> list:
    return [
        Container(
            key="pd_preview_footer",
            width="match",
            bg=Colors.with_opacity(Colors.BLACK, 0.72),
            padding=pad(horizontal=Spacing.MD, vertical=Spacing.XS + 2),
            child=Row(
                key="pd_preview_footer_row",
                spacing=Spacing.SM,
                vertical_alignment="center",
                children=[
                    sync_pill(),
                    Container(key="pd_preview_footer_spacer", expand=1),
                    Icon(Icons.LOGOUT, key="pd_preview_footer_exit",
                         size=16,
                         color=Colors.with_opacity(Colors.WHITE, 0.85)
                         ).on_click(lambda _e: exit_preview()),
                ],
            ),
        ),
    ]


def _leave(live: bool) -> None:
    if live:
        handle_back()
    else:
        exit_preview()


def _summary_surface() -> Widget:
    """Connecting / failed / disconnected — with context and actions."""
    state = session.state
    if session.is_busy:
        return _busy_surface(state)
    if state == ConnectionState.FAILED:
        return _failed_surface()
    return _idle_surface()


def _busy_surface(state: str) -> Widget:
    from app.components.states import NoticeState

    detail = {
        ConnectionState.CONNECTING: "Reaching the development server…",
        ConnectionState.HANDSHAKING:
            "Checking protocol versions and credentials…",
        ConnectionState.RECONNECTING:
            f"Retry {session.reconnect_attempt} — the link dropped.",
    }.get(state, "Connecting…")
    return _dark_surface(
        NoticeState(
            "pd_preview_notice_busy",
            icon=Icons.SYNC,
            title="Connecting",
            message=detail,
            tone="pending",
            progress=True,
        ))


def _failed_surface() -> Widget:
    from app.components.states import NoticeState

    return _dark_surface(
        NoticeState(
            "pd_preview_notice_failed",
            icon=Icons.WARNING,
            title="Preview unavailable",
            message=session.describe_error()
            or "The development server could not be reached.",
            tone="error",
            action="Retry",
            on_action=lambda _event: session.reconnect(),
        ))


def _idle_surface() -> Widget:
    from app.components.states import NoticeState

    return _dark_surface(
        NoticeState(
            "pd_preview_notice_idle",
            icon=Icons.QR_CODE,
            title="No live session",
            message="Scan the QR code printed by `pydrud dev` to start "
                    "previewing a project here.",
            tone="idle",
            action="Scan now",
            on_action=lambda _event: router.push("scan"),
        ))


def _dark_surface(child: Widget) -> Widget:
    return Container(
        key="pd_preview_dim",
        width="match",
        height="match",
        bg=Theme.background,
        alignment="center",
        padding=Spacing.XL,
        child=child,
    )


def _manage_chrome(live: bool) -> None:
    """Keep-awake and system bars follow the session, not the screen."""
    app = current()
    page = app.page if app is not None else None
    if page is None:
        return
    if live and keep_awake.value:
        page.keep_awake(True)
    elif not live and keep_awake.value:
        page.keep_awake(False)
