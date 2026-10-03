"""Settings — appearance, connection behaviour, protocol info and About."""

from __future__ import annotations

from pydrud import (
    Button, Card, Column, Container, Divider, Icon, Icons, ListTile, Radius,
    Row, SegmentedButton, Spacing, Switch, Text, Theme, Widget,
)

from app.components import CodeChip, MetaList, MetaRow, section
from app.config import (
    APP_NAME, APP_TAGLINE, APP_VERSION, CLIENT_NAME, PYDASH_REPO,
    PYDRUD_REPO, PYDRUD_VERSION, PREVIEW_PROTOCOL_VERSION,
    RENDERER_PROTOCOL_VERSION,
)
from app.preview.session import session
from app.runtime import current, refresh
from app.state import auto_reconnect, brand_seed, haptics_enabled, keep_awake
from app.state import theme_mode
from app.theme import status_color

__all__ = ["body"]


def body() -> list:
    return [
        _appearance_card(),
        _connection_card(),
        _protocol_card(),
        _about_card(),
    ]


# ── appearance ──────────────────────────────────────────────────────────────

def _appearance_card() -> Widget:
    from app.config import ACCENT

    mode = theme_mode.value
    return Card(
        key="pd_set_appearance",
        padding=Spacing.LG,
        child=Column(
            key="pd_set_appearance_col",
            spacing=Spacing.MD,
            children=[
                section("Appearance", "pd_set_appearance_sec"),
                SegmentedButton(
                    ["System", "Light", "Dark"],
                    key="pd_set_mode",
                    selected={"system": 0, "light": 1, "dark": 2}.get(mode, 0),
                ).on_change(_set_mode),
                Text("Pydash follows the system theme by default; a "
                     "previewed project may restyle the client while its "
                     "session is live.",
                     key="pd_set_mode_note", size=12,
                     color=Theme.text_secondary),
            ],
        ),
    )


def _set_mode(event) -> None:
    try:
        index = int(event.get("value", 0))
    except (TypeError, ValueError):
        return
    mode = ("system", "light", "dark")[max(0, min(index, 2))]
    theme_mode.value = mode
    page = _page()
    if page is not None:
        page.set_theme_mode(mode)
    refresh()


# ── connection ──────────────────────────────────────────────────────────────

def _connection_card() -> Widget:
    return Card(
        key="pd_set_connection",
        padding=Spacing.LG,
        child=Column(
            key="pd_set_connection_col",
            spacing=Spacing.MD,
            children=[
                section("Connection", "pd_set_connection_sec"),
                Switch("Auto-reconnect when the link drops",
                       key="pd_set_reconnect", active=auto_reconnect.value
                       ).on_change(_toggle_reconnect),
                Switch("Haptic ticks on connection events",
                       key="pd_set_haptics", active=haptics_enabled.value
                       ).on_change(_toggle_haptics),
                Switch("Keep the screen awake while previewing",
                       key="pd_set_awake", active=keep_awake.value
                       ).on_change(_toggle_awake),
                Divider(key="pd_set_conn_div"),
                ListTile("End the preview session",
                         key="pd_set_disconnect",
                         subtitle="Closes the socket and restores Pydash's "
                                  "own theme",
                         leading=Icons.LOGOUT,
                         enabled=session.is_live or session.is_busy,
                         on_click=lambda _e: _disconnect()),
            ],
        ),
    )


def _toggle_reconnect(event) -> None:
    auto_reconnect.value = bool(event.get("value", True))
    refresh()


def _toggle_haptics(event) -> None:
    haptics_enabled.value = bool(event.get("value", True))
    refresh()


def _toggle_awake(event) -> None:
    keep_awake.value = bool(event.get("value", False))
    page = _page()
    if page is not None and not session.is_live:
        page.keep_awake(keep_awake.value)
    refresh()


def _disconnect() -> None:
    session.disconnect(reason="closed from Settings")
    refresh()


# ── protocol info ───────────────────────────────────────────────────────────

def _protocol_card() -> Widget:
    return Card(
        key="pd_set_protocol",
        padding=Spacing.LG,
        child=Column(
            key="pd_set_protocol_col",
            spacing=Spacing.MD,
            children=[
                section("Runtime & protocol", "pd_set_protocol_sec"),
                MetaList("pd_set_protocol_meta", [
                    MetaRow("pd_set_proto_client", "Client",
                            f"{CLIENT_NAME} {APP_VERSION}", icon=Icons.SPARKLE),
                    MetaRow("pd_set_proto_sdk", "Pydrud SDK",
                            PYDRUD_VERSION, icon=Icons.PYTHON),
                    MetaRow("pd_set_proto_preview", "Preview protocol",
                            f"v{PREVIEW_PROTOCOL_VERSION}", icon=Icons.LINK),
                    MetaRow("pd_set_proto_renderer", "Renderer protocol",
                            f"v{RENDERER_PROTOCOL_VERSION}", icon=Icons.LAYERS),
                ]),
                Text("The handshake exchanges protocol versions and session "
                     "credentials before the first UI snapshot is sent.",
                     key="pd_set_protocol_note", size=12,
                     color=Theme.text_secondary),
                CodeChip(
                    "pd_set_proto_uri",
                    "pydrud://preview/connect?host=…&session=…&token=…",
                    full=True),
            ],
        ),
    )


# ── about ───────────────────────────────────────────────────────────────────

def _about_card() -> Widget:
    return Card(
        key="pd_set_about",
        padding=Spacing.LG,
        child=Column(
            key="pd_set_about_col",
            spacing=Spacing.MD,
            children=[
                section("About", "pd_set_about_sec"),
                Row(
                    key="pd_set_about_brand",
                    spacing=Spacing.MD,
                    vertical_alignment="center",
                    children=[
                        Container(
                            key="pd_set_about_mark",
                            width=44,
                            height=44,
                            border_radius=Radius.MD,
                            bg=Theme.primary,
                            alignment="center",
                            child=Icon(Icons.SPARKLE,
                                       key="pd_set_about_mark_icon", size=22,
                                       color=Theme.on_primary),
                        ),
                        Column(
                            key="pd_set_about_brand_col",
                            spacing=2,
                            expand=1,
                            children=[
                                Text(APP_NAME, key="pd_set_about_name",
                                     size=16, weight=800, color=Theme.text),
                                Text(APP_TAGLINE,
                                     key="pd_set_about_tagline", size=12,
                                     color=Theme.text_secondary),
                            ],
                        ),
                    ],
                ),
                Divider(key="pd_set_about_div"),
                ListTile("Pydrud on GitHub",
                         key="pd_set_about_pydrud_repo",
                         subtitle=PYDRUD_REPO.replace("https://", ""),
                         leading=Icons.PYTHON,
                         on_click=lambda _e: _open(PYDRUD_REPO)),
                ListTile("Pydash on GitHub",
                         key="pd_set_about_pydash_repo",
                         subtitle=PYDASH_REPO.replace("https://", ""),
                         leading=Icons.CODE,
                         on_click=lambda _e: _open(PYDASH_REPO)),
                Divider(key="pd_set_about_div2"),
                MetaList("pd_set_about_meta", [
                    MetaRow("pd_set_about_version", "Version", APP_VERSION),
                    MetaRow("pd_set_about_framework", "Built with",
                            f"Pydrud {PYDRUD_VERSION}"),
                ]),
            ],
        ),
    )


def _open(url: str) -> None:
    page = _page()
    if page is None:
        return
    page.invoke("open_url", url=url)


def _page():
    app = current()
    return app.page if app is not None else None
