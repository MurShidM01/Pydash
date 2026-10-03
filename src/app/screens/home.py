"""Home — the connection dashboard.

Answers, in order: *Am I connected? To what? Did it sync? What do I do
next?* The primary action is always scanning the `pydrud dev` QR code;
once a session is live the same screen becomes its control panel with
server details, live statistics and reconnect/disconnect controls.
"""

from __future__ import annotations

from typing import Optional

from pydrud import (
    Button, Card, Colors, Column, Container, Divider, Icon, Icons, Radius,
    Row, Spacing, Text, Theme, Widget,
)

from app.components import (
    BrandHero, CodeChip, MetaList, MetaRow, StatusPill, section,
)
from app.config import (
    APP_VERSION, PREVIEW_PROTOCOL_VERSION, RENDERER_PROTOCOL_VERSION,
)
from app.preview.models import ConnectionState, Endpoint
from app.preview.session import session
from app.preview.uri import (
    PreviewTarget, parse_preview_uri,
)
from app.runtime import refresh, router
from app.state import last_endpoint
from app.theme import status_color

__all__ = ["body"]


def body() -> list:
    """The Home tab's sections."""
    return [
        BrandHero("pd_home_hero", _hero_subtitle()),
        _connection_card(),
        _how_it_works_card(),
        _about_card(),
    ]


def _hero_subtitle() -> str:
    if session.is_live:
        return f"Previewing {session.project_name}"
    if session.state == ConnectionState.RECONNECTING:
        return "Reconnecting to the development server…"
    return "Scan, connect, see your UI — live"


# ── connection card ─────────────────────────────────────────────────────────

def _connection_card() -> Widget:
    state = session.state

    if session.is_live:
        return _live_card()
    if session.is_busy:
        return _busy_card()
    if state == ConnectionState.FAILED:
        return _failed_card()
    return _idle_card()


def _idle_card() -> Widget:
    reconnect = _reconnect_row()
    return Card(
        key="pd_home_idle",
        padding=Spacing.LG,
        child=Column(
            key="pd_home_idle_col",
            spacing=Spacing.LG,
            children=[
                _status_row("pd_home_idle_status"),
                Text("Run `pydrud dev` in your project, then point Pydash "
                     "at the QR code it prints. Your UI appears here the "
                     "moment it connects.",
                     key="pd_home_idle_hint", size=13,
                     color=Theme.text_secondary),
                Button("Scan QR code", key="pd_home_scan", icon=Icons.QR_CODE,
                       full_width=True, size="lg"
                       ).on_click(lambda _e: router.push("scan", mode="scan")),
                Button("Connect manually", key="pd_home_manual",
                       variant="tonal", icon=Icons.EDIT, full_width=True
                       ).on_click(lambda _e: router.push("scan",
                                                         mode="manual")),
                reconnect,
            ],
        ),
    )


def _reconnect_row() -> Widget:
    endpoint = _stored_endpoint()
    if endpoint is None:
        return Container(key="pd_home_no_recent", height=0)
    return Column(
        key="pd_home_recent",
        spacing=Spacing.SM,
        children=[
            Divider(key="pd_home_recent_div"),
            Text("Last session", key="pd_home_recent_label", size=12,
                 weight=700, color=Theme.text_secondary,
                 style={"font": {"letterSpacing": 0.08}}),
            Text(f"{endpoint.project_name} · {endpoint.describe()}",
                 key="pd_home_recent_value", size=13,
                 color=Theme.text_secondary),
            Button("Reconnect", key="pd_home_reconnect", variant="outlined",
                   size="sm", icon=Icons.SYNC
                   ).on_click(lambda _e: _reconnect(endpoint)),
        ],
    )


def _stored_endpoint() -> Optional[Endpoint]:
    stored = last_endpoint.value
    if not stored or not isinstance(stored, dict):
        return None
    if not stored.get("session_id") or not stored.get("token"):
        return None
    return Endpoint(
        host=str(stored.get("host", "")),
        port=int(stored.get("port", 0) or 0),
        session_id=str(stored["session_id"]),
        token=str(stored["token"]),
        project_id=str(stored.get("project_id", "")),
        project_name=str(stored.get("project_name", "")),
    )


def _reconnect(endpoint: Endpoint) -> None:
    session.connect(endpoint)
    router.push("preview")


def _busy_card() -> Widget:
    label = {
        ConnectionState.CONNECTING: "Reaching the development server",
        ConnectionState.HANDSHAKING: "Verifying session & protocols",
        ConnectionState.RECONNECTING: "Reconnecting",
    }.get(session.state, "Connecting")
    detail = ("" if session.state != ConnectionState.RECONNECTING
              else f"attempt {session.reconnect_attempt}")
    return Card(
        key="pd_home_busy",
        padding=Spacing.LG,
        child=Column(
            key="pd_home_busy_col",
            spacing=Spacing.MD,
            children=[
                _status_row("pd_home_busy_status"),
                Row(
                    key="pd_home_busy_row",
                    spacing=Spacing.MD,
                    vertical_alignment="center",
                    children=[
                        Icon(Icons.SYNC, key="pd_home_busy_icon", size=20,
                             color=Theme.primary),
                        Column(
                            key="pd_home_busy_text",
                            spacing=2,
                            expand=1,
                            children=[
                                Text(label, key="pd_home_busy_label",
                                     size=14, weight=600,
                                     color=Theme.text),
                                Text(detail or session.endpoint.describe()
                                     if session.endpoint else detail,
                                     key="pd_home_busy_detail", size=12,
                                     color=Theme.text_secondary),
                            ],
                        ),
                    ],
                ),
            ],
        ),
    )


def _failed_card() -> Widget:
    return Card(
        key="pd_home_failed",
        padding=Spacing.LG,
        child=Column(
            key="pd_home_failed_col",
            spacing=Spacing.MD,
            children=[
                _status_row("pd_home_failed_status"),
                Text(session.describe_error()
                     or "The development server could not be reached.",
                     key="pd_home_failed_error", size=13,
                     color=Theme.text_secondary),
                Row(
                    key="pd_home_failed_actions",
                    spacing=Spacing.SM,
                    children=[
                        Button("Retry", key="pd_home_retry", icon=Icons.REFRESH
                               ).on_click(lambda _e: session.reconnect()),
                        Button("Scan again", key="pd_home_rescan",
                               variant="tonal", icon=Icons.QR_CODE
                               ).on_click(lambda _e: router.push("scan", mode="scan")),
                    ],
                ),
            ],
        ),
    )


def _live_card() -> Widget:
    stats = session.stats
    endpoint = session.endpoint
    server = session.server
    return Column(
        key="pd_home_live",
        spacing=Spacing.LG,
        children=[
            _live_hero(),
            Card(
                key="pd_home_live_details",
                padding=Spacing.LG,
                child=Column(
                    key="pd_home_live_details_col",
                    spacing=Spacing.MD,
                    children=[
                        section("Server", "pd_home_live_sec"),
                        MetaList("pd_home_live_meta", [
                            MetaRow("pd_home_live_project", "Project",
                                    session.project_name, icon=Icons.FOLDER),
                            MetaRow("pd_home_live_host", "Address",
                                    endpoint.describe() if endpoint else "—",
                                    icon=Icons.SERVER, mono=True),
                            MetaRow("pd_home_live_session", "Session",
                                    (server.session_id[:13] + "…")
                                    if server and server.session_id else "—",
                                    icon=Icons.KEY, mono=True),
                            MetaRow("pd_home_live_proto", "Protocols",
                                    f"preview v{PREVIEW_PROTOCOL_VERSION} · "
                                    f"renderer v{RENDERER_PROTOCOL_VERSION}",
                                    icon=Icons.LAYERS, mono=True),
                            MetaRow("pd_home_live_sync", "Last sync",
                                    stats.describe_last_sync(),
                                    icon=Icons.SYNC),
                            MetaRow("pd_home_live_nodes", "Tree size",
                                    f"{session.tree.node_count()} nodes",
                                    icon=Icons.GRID),
                        ]),
                    ],
                ),
            ),
            Card(
                key="pd_home_live_stats",
                padding=Spacing.LG,
                child=Column(
                    key="pd_home_live_stats_col",
                    spacing=Spacing.MD,
                    children=[
                        section("Session traffic", "pd_home_live_stats_sec"),
                        Row(
                            key="pd_home_live_stats_row",
                            spacing=Spacing.SM,
                            children=[
                                _stat("pd_home_stat_rev", "Revision",
                                      str(stats.revision)),
                                _stat("pd_home_stat_snaps", "Snapshots",
                                      str(stats.snapshots)),
                                _stat("pd_home_stat_patches", "Patches",
                                      str(stats.patches)),
                                _stat("pd_home_stat_ops", "Patch ops",
                                      str(stats.applied_ops)),
                            ],
                        ),
                        Text("Edit any Python file on your computer and "
                             "watch these numbers move.",
                             key="pd_home_live_stats_hint", size=12,
                             color=Theme.text_secondary),
                    ],
                ),
            ),
            Row(
                key="pd_home_live_actions",
                spacing=Spacing.SM,
                children=[
                    Button("Open live preview", key="pd_home_open",
                           icon=Icons.PLAY_CIRCLE, expand=1, size="lg"
                           ).on_click(lambda _e: router.push("preview")),
                    Button("", key="pd_home_disconnect", icon=Icons.CLOSE,
                           variant="outlined", size="lg",
                           ).on_click(lambda _e: _disconnect()),
                ],
            ),
        ],
    )


def _stat(key: str, label: str, value: str) -> Widget:
    return Container(
        key=f"{key}_box",
        expand=1,
        padding=Spacing.MD,
        border_radius=Radius.MD,
        bg=Theme.surface_variant,
        child=Column(
            key=f"{key}_col",
            spacing=2,
            horizontal_alignment="center",
            children=[
                Text(value, key=f"{key}_value", size=17, weight=800,
                     color=Theme.primary),
                Text(label.upper(), key=f"{key}_label", size=9, weight=700,
                     color=Theme.text_secondary,
                     style={"font": {"letterSpacing": 0.08}}),
            ],
        ),
    )


def _live_hero() -> Widget:
    stats = session.stats
    return Container(
        key="pd_home_live_hero",
        width="match",
        border_radius=Radius.XL,
        padding=Spacing.XL,
        style={
            "gradient": {
                "colors": [Colors.SUCCESS, Colors.mix(
                    Colors.SUCCESS, Theme.secondary, 0.6)],
                "direction": "diagonal",
            },
        },
        child=Row(
            key="pd_home_live_hero_row",
            spacing=Spacing.LG,
            vertical_alignment="center",
            children=[
                Container(
                    key="pd_home_live_hero_ring",
                    width=52,
                    height=52,
                    border_radius=Radius.PILL,
                    bg=Colors.with_opacity(Colors.WHITE, 0.2),
                    alignment="center",
                    child=Icon(Icons.ANDROID, key="pd_home_live_hero_icon",
                               size=26, color=Colors.WHITE),
                ),
                Column(
                    key="pd_home_live_hero_col",
                    spacing=2,
                    expand=1,
                    children=[
                        Text(session.project_name,
                             key="pd_home_live_hero_title", size=19,
                             weight=800, color=Colors.WHITE, max_lines=1,
                             overflow="ellipsis"),
                        Text(f"Connected · rev {stats.revision} · "
                             f"{stats.describe_last_sync()}",
                             key="pd_home_live_hero_sub", size=12,
                             color=Colors.with_opacity(Colors.WHITE, 0.9)),
                    ],
                ),
                Text("LIVE", key="pd_home_live_hero_badge", size=11,
                     weight=800, color=Colors.WHITE,
                     style={"font": {"letterSpacing": 0.16}}),
            ],
        ),
    )


def _status_row(key: str) -> Widget:
    from app.preview.models import STATE_HINTS, STATE_LABELS

    state = session.state
    return Row(
        key=f"{key}_line",
        spacing=Spacing.SM,
        vertical_alignment="center",
        children=[
            StatusPill(key, state),
            Text(STATE_HINTS.get(state, ""), key=f"{key}_hint", size=12,
                 color=Theme.text_secondary, expand=1),
        ],
    )


def _disconnect() -> None:
    session.disconnect(reason="closed from the dashboard")
    refresh()


# ── guidance ────────────────────────────────────────────────────────────────

def _how_it_works_card() -> Widget:
    steps = (
        ("Run the dev server",
         "In your Pydrud project:", "pydrud dev"),
        ("Scan the QR code",
         "It appears in the terminal — Pydash reads it with the camera.",
         None),
        ("Edit and save",
         "Every save re-renders here in milliseconds. No APK, no install.",
         None),
    )
    rows: list[Widget] = []
    for index, (title, note, command) in enumerate(steps):
        rows.append(Row(
            key=f"pd_home_step{index}",
            spacing=Spacing.MD,
            vertical_alignment="center",
            children=[
                Container(
                    key=f"pd_home_step{index}_num",
                    width=28,
                    height=28,
                    border_radius=Radius.PILL,
                    bg=Colors.with_opacity(Theme.primary, 0.12),
                    alignment="center",
                    child=Text(str(index + 1),
                               key=f"pd_home_step{index}_num_t", size=13,
                               weight=800, color=Theme.primary),
                ),
                Column(
                    key=f"pd_home_step{index}_col",
                    spacing=4,
                    expand=1,
                    children=[
                        Text(title, key=f"pd_home_step{index}_t", size=14,
                             weight=600, color=Theme.text),
                        Text(note, key=f"pd_home_step{index}_n", size=12,
                             color=Theme.text_secondary),
                        *([CodeChip(f"pd_home_step{index}_code", command)]
                          if command else []),
                    ],
                ),
            ],
        ))
    return Card(
        key="pd_home_how",
        padding=Spacing.LG,
        child=Column(
            key="pd_home_how_col",
            spacing=Spacing.LG,
            children=[
                section("How it works", "pd_home_how_sec"),
                *rows,
            ],
        ),
    )


def _about_card() -> Widget:
    from app.config import PYDRUD_VERSION

    return Card(
        key="pd_home_about",
        padding=Spacing.LG,
        child=Column(
            key="pd_home_about_col",
            spacing=Spacing.MD,
            children=[
                section("About", "pd_home_about_sec"),
                MetaList("pd_home_about_meta", [
                    MetaRow("pd_home_about_app", "Pydash", APP_VERSION,
                            icon=Icons.SPARKLE),
                    MetaRow("pd_home_about_fw", "Pydrud SDK",
                            PYDRUD_VERSION, icon=Icons.PYTHON),
                ]),
                Text("Pydash is the preview client; your machine runs the "
                     "project. Find both on GitHub.",
                     key="pd_home_about_note", size=12,
                     color=Theme.text_secondary),
            ],
        ),
    )
