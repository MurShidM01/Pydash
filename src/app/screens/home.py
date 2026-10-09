"""Home — the dashboard: connect, watch the session, learn the flow.

Home is the first thing the user sees and the only place a session is
started. It has four faces, chosen by the live state of
:data:`app.preview.session`:

* **idle** — the two ways in (scan a QR code, paste a URL) plus the
  "how it works" explainer and, if there is one, the last session;
* **busy** — a progress card with the step the handshake is on and a cancel;
* **failed** — a red notice with the friendly reason and a retry;
* **live** — the project card: identity, live counters and the way into the
  immersive preview.

Everything is rebuilt from the reactive session each time the app refreshes,
so the dashboard is never stale.
"""

from __future__ import annotations

from pydrud import (
    Button,
    Column,
    Container,
    Icon,
    Icons,
    LinearProgress,
    ListTile,
    OutlinedButton,
    Row,
    Text,
    TextButton,
)

from app import connection, recents, state, theme
from app.components import (
    brand_hero,
    card,
    meta_list,
    notice_state,
    section_header,
    spinner,
    stat_tile,
    step_row,
    status_dot,
)
from app.config import APP_NAME, APP_VERSION, PYDRUD_VERSION
from app.preview import session
from app.preview.models import (
    STATE_HINTS,
    STATE_LABELS,
    ConnectionState,
    Endpoint,
)
from app.runtime import refresh, router

__all__ = ["body"]


def body() -> Column:
    """The scrollable Home tab body."""
    children = [brand_hero(footer=_hero_footer()), _primary_actions()]

    section = _session_section()
    if section is not None:
        children.append(section)

    recent = _recent_section()
    if recent is not None:
        children.append(recent)

    children.append(_how_it_works())
    children.append(_footer())

    return Column(
        key="pd_home",
        class_="pd-screen",
        scroll=True,
        spacing=18,
        style={"padding": theme.page_insets(top=16, bottom=28)},
        children=children,
    )


# ── hero ─────────────────────────────────────────────────────────────────────


def _hero_footer() -> Row:
    label = STATE_LABELS.get(session.state, "Ready")
    return Row(
        key="pd_hero_footer",
        spacing=8,
        main_axis_size="min",
        vertical_alignment="center",
        children=[
            Container(
                key="pd_hero_dot",
                style={"width": 9, "height": 9, "borderRadius": 999,
                       "bg": theme.status_color(session.state)},
            ),
            Text(label, key="pd_hero_footer_text", class_="pd-hero-caption",
                 max_lines=1),
        ],
    )


# ── actions ──────────────────────────────────────────────────────────────────


def _primary_actions() -> Column:
    if session.is_live:
        return Column(key="pd_actions", spacing=10, children=[
            Button("Open live preview", icon=Icons.PLAY_ARROW, full_width=True,
                   size="lg", on_click=lambda _e: _open_preview()),
            OutlinedButton("Disconnect", icon=Icons.LOGOUT, full_width=True,
                           on_click=lambda _e: _disconnect()),
        ])
    busy = session.is_busy
    return Column(key="pd_actions", spacing=10, children=[
        Button("Scan QR code", icon=Icons.QR_CODE, full_width=True, size="lg",
               disabled=busy, on_click=lambda _e: _open_scan("scan")),
        OutlinedButton("Enter connection URL", icon=Icons.LINK,
                       full_width=True, disabled=busy,
                       on_click=lambda _e: _open_scan("manual")),
    ])


# ── session state ────────────────────────────────────────────────────────────


def _session_section():
    if session.is_live:
        return _live_card()
    if session.is_busy:
        return _busy_card()
    if session.state == ConnectionState.FAILED:
        return _failed_card()
    return None


def _live_card() -> Container:
    stats = session.stats
    host = session.endpoint.describe() if session.endpoint else "—"
    return card(key="pd_live_card", accent=True, spacing=14, child=[
        Row(
            key="pd_live_head",
            spacing=10,
            main_axis_size="max",
            vertical_alignment="center",
            children=[
                status_dot(key="pd_live_dot", size=10),
                Text(session.project_name, key="pd_live_name", class_="pd-h2",
                     expand=1, max_lines=1),
                Container(
                    key="pd_live_tag",
                    class_="pd-tag",
                    style={"bg": theme.status_surface("connected"),
                           **theme.status_border("connected")},
                    child=Text("LIVE", key="pd_live_tag_text",
                               class_="pd-pill-text",
                               style={"color": theme.success()},
                               max_lines=1, overflow="clip"),
                ),
            ],
        ),
        meta_list([
            ("Host", host),
            ("Revision", stats.revision),
            ("Last sync", stats.describe_last_sync()),
        ], key="pd_live_meta"),
        Row(key="pd_live_stats", spacing=10, children=[
            stat_tile(stats.snapshots, "SNAPSHOTS", key="pd_stat_snapshots"),
            stat_tile(stats.patches, "PATCHES", key="pd_stat_patches"),
            stat_tile(stats.events_sent, "EVENTS", key="pd_stat_events"),
        ]),
    ])


def _busy_card() -> Container:
    label = STATE_LABELS.get(session.state, "Connecting…")
    hint = STATE_HINTS.get(session.state, "")
    return card(key="pd_busy_card", tint=True, spacing=12, child=[
        Row(
            key="pd_busy_head",
            spacing=10,
            main_axis_size="max",
            vertical_alignment="center",
            children=[
                status_dot(key="pd_busy_dot", size=10),
                Text(label, key="pd_busy_label", class_="pd-h2", expand=1,
                     max_lines=1),
            ],
        ),
        LinearProgress(key="pd_busy_bar", indeterminate=True,
                       color=theme.primary()),
        Text(hint, key="pd_busy_hint", class_="pd-body"),
        OutlinedButton("Cancel", icon=Icons.CLOSE, full_width=True,
                       on_click=lambda _e: _cancel()),
    ])


def _failed_card() -> Container:
    message = session.describe_error() or STATE_HINTS.get(
        ConnectionState.FAILED, "")
    return notice_state(
        Icons.ERROR,
        "Could not connect",
        message,
        key="pd_failed",
        tone="danger",
        action=Row(
            key="pd_failed_actions",
            spacing=10,
            main_axis_size="min",
            children=[
                Button("Retry", icon=Icons.REFRESH,
                       on_click=lambda _e: _retry()),
                OutlinedButton("Scan again",
                               on_click=lambda _e: _open_scan("scan")),
            ],
        ),
    )


def _recent_section():
    """The recent-apps shortcut: tap a row to re-check that project's link.

    Rows expire on their own (see :mod:`app.recents`), so this section is a
    live view rather than a growing history. It stays visible even while a
    session is live, so the list is always there to switch projects from.
    Tapping one runs the same connect-and-spin flow as the scanner, with the
    spinner shown on the row.
    """
    items = recents.entries()
    if not items:
        return None
    return Column(key="pd_recent", spacing=10, children=[
        section_header(
            "Recent apps", caption="TAP TO RECONNECT", key="pd_recent_section",
            action=TextButton("Clear", on_click=lambda _e: _clear_recents()),
        ),
        card(key="pd_recent_card", spacing=0,
             child=[_recent_row(index, entry)
                    for index, entry in enumerate(items)]),
    ])


def _recent_row(index: int, entry: dict) -> ListTile:
    """One single-line recent-app tile — as compact as a Settings link row.

    The old two-line tile carried the host and age in a subtitle, which made
    every row twice as tall as the "Learn more" tiles it sits beside. The age
    now rides in the trailing slot as a quiet caption, so the row keeps its
    freshness signal without the extra line.
    """
    endpoint = Endpoint.from_dict(entry)
    if _is_checking(entry):
        trailing = spinner(size=20, key=f"pd_recent_spin_{index}")
    else:
        age = recents.age_label(entry)
        tail: list = []
        if age:
            tail.append(Text(age, key=f"pd_recent_age_{index}",
                             class_="pd-caption", max_lines=1))
        tail.append(Icon(Icons.CHEVRON_RIGHT, key=f"pd_recent_chev_{index}",
                         size=18, color=theme.text_secondary()))
        trailing = Row(key=f"pd_recent_tail_{index}", spacing=6,
                       main_axis_size="min", vertical_alignment="center",
                       children=tail)
    return ListTile(
        endpoint.project_name or endpoint.host or "Pydrud project",
        leading=Icons.PLAY_ARROW,
        trailing=trailing,
        on_click=lambda _e: _open_recent(entry),
        key=f"pd_recent_{index}",
    )


def _is_checking(entry: dict) -> bool:
    """Whether this row is the one whose connection is being checked."""
    if not state.connecting.value:
        return False
    target = state.connecting_endpoint.value
    if not isinstance(target, dict):
        return False
    return (str(target.get("host", "")) == str(entry.get("host", ""))
            and _port(target) == _port(entry))


def _port(payload: dict) -> int:
    try:
        return int(payload.get("port", 0) or 0)
    except (TypeError, ValueError):
        return 0


# ── explainer ────────────────────────────────────────────────────────────────


def _how_it_works() -> Column:
    return Column(key="pd_how", spacing=10, children=[
        section_header("How it works", caption="NO APK REBUILDS",
                       key="pd_how_section"),
        card(key="pd_how_card", spacing=16, child=[
            step_row(1, "Start the dev server",
                     "Run `pydrud dev` in your project. It prints a QR code "
                     "with the address and a one-run key.",
                     key="pd_step_one"),
            step_row(2, "Scan it with Pydash",
                     "Point your camera at the code, or paste the URL. Pydash "
                     "connects over the local network.",
                     key="pd_step_two"),
            step_row(3, "Edit and watch",
                     "Every save re-renders here natively. No rebuild, no "
                     "reinstall, no cables.",
                     key="pd_step_three"),
        ]),
    ])


def _footer() -> Container:
    return Container(
        key="pd_home_footer_box",
        width="match",
        alignment="center",
        child=Text(
            f"{APP_NAME} {APP_VERSION}  ·  Pydrud {PYDRUD_VERSION}",
            key="pd_home_footer", class_="pd-caption",
        ),
    )


# ── actions ──────────────────────────────────────────────────────────────────


def _open_scan(mode: str) -> None:
    router.push("scan", mode=mode)


def _open_preview() -> None:
    # Adopt the previewed palette before the route builds (see renderer).
    from app.preview.renderer import adopt_remote_theme

    try:
        adopt_remote_theme()
    except Exception:
        pass
    router.push("preview")


def _disconnect() -> None:
    session.disconnect()
    refresh()


def _cancel() -> None:
    connection.cancel()


def _retry() -> None:
    connection.retry()


def _open_recent(entry: dict) -> None:
    """Re-check a recent project's link, showing the spinner on its row.

    Tapping a recent while another session is live switches to it: the current
    session is closed first so the connect flow starts from a clean slate.
    """
    if state.connecting.value or session.is_busy:
        return
    if session.is_live:
        session.disconnect()
    endpoint = Endpoint.from_dict(entry)
    recents.touch(endpoint)
    connection.start(endpoint, origin="home")


def _clear_recents() -> None:
    recents.clear()
    refresh()
