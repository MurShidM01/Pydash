"""Settings — control Pydash and read what it is made of.

Three groups:

* **Appearance** — the light / dark / system switch, applied live through
  :func:`app.theme.apply_theme_mode`;
* **Behaviour** — auto-reconnect, haptics and keep-awake, each mirrored into
  the reactive state the rest of the app reads;
* **About** — versions and protocol numbers, plus the device facts
  (manufacturer, model, Android SDK) fetched once from the native layer.

Every choice is written through :mod:`app.prefs`, so the app opens the way it
was left.
"""

from __future__ import annotations

from typing import Any

from pydrud import (
    Column,
    Container,
    Icons,
    ListTile,
    SegmentedButton,
    State,
    SwitchListTile,
    Text,
)

from app import prefs, state, theme
from app.components import card, meta_list, section_header
from app.config import (
    APP_NAME,
    APP_VERSION,
    PACKAGE,
    PREVIEW_PROTOCOL_VERSION,
    PYDRUD_DOCS,
    PYDRUD_REPO,
    PYDRUD_VERSION,
    RENDERER_PROTOCOL_VERSION,
)
from app.runtime import current, refresh

__all__ = ["body"]

_MODES = ("system", "light", "dark")
_MODE_LABELS = ("System", "Light", "Dark")
_MODE_ICONS = (Icons.SYNC, Icons.LIGHT_MODE, Icons.DARK_MODE)

#: Device facts from the native layer (``None`` until the first read resolves).
device_info = State(None, name="pd_device_info")
_device_loaded = False


def body() -> Column:
    """The scrollable Settings tab body."""
    return Column(
        key="pd_settings",
        class_="pd-screen",
        scroll=True,
        spacing=18,
        style={"padding": theme.page_insets(top=16, bottom=28)},
        children=[
            _appearance(),
            _behaviour(),
            _about(),
            _links(),
            _footer(),
        ],
    )


# ── appearance ───────────────────────────────────────────────────────────────


def _appearance() -> Column:
    return Column(key="pd_appearance", spacing=10, children=[
        section_header("Appearance", caption="THEME",
                       key="pd_appearance_section"),
        card(key="pd_appearance_card", spacing=12, child=[
            Text("Theme mode", key="pd_theme_title", class_="pd-meta-val"),
            SegmentedButton(
                list(_MODE_LABELS),
                selected=_mode_index(),
                icons=list(_MODE_ICONS),
                on_change=_on_theme_change,
                key="pd_theme_segmented",
            ),
            Text(
                "Pydash follows the system by default. A connected project may "
                "re-theme the app while it is on screen; Pydash restores its "
                "own palette when the session ends.",
                key="pd_theme_hint", class_="pd-body",
            ),
        ]),
    ])


def _mode_index() -> int:
    try:
        return _MODES.index(str(state.theme_mode.value))
    except ValueError:
        return 0


def _on_theme_change(event) -> None:
    try:
        index = int(event.value)
    except (TypeError, ValueError):
        index = 0
    if not 0 <= index < len(_MODES):
        index = 0
    mode = _MODES[index]
    state.theme_mode.value = mode
    page = _page()
    if page is not None:
        theme.apply_theme_mode(page, mode)
    prefs.save(theme_mode=mode)
    refresh()


# ── behaviour ────────────────────────────────────────────────────────────────


def _behaviour() -> Column:
    return Column(key="pd_behaviour", spacing=10, children=[
        section_header("Connection & feedback", caption="BEHAVIOUR",
                       key="pd_behaviour_section"),
        card(key="pd_behaviour_card", spacing=0, child=[
            SwitchListTile(
                "Auto-reconnect", key="pd_switch_reconnect",
                control_key="pd_control_reconnect",
                value=bool(state.auto_reconnect.value),
                subtitle="Retry automatically when the dev server restarts.",
                on_change=lambda e: _set_bool(
                    state.auto_reconnect, "auto_reconnect", e),
            ),
            _divider("pd_div_reconnect"),
            SwitchListTile(
                "Haptics", key="pd_switch_haptics",
                control_key="pd_control_haptics",
                value=bool(state.haptics_enabled.value),
                subtitle="A short tick on connect, disconnect and errors.",
                on_change=lambda e: _set_bool(
                    state.haptics_enabled, "haptics_enabled", e),
            ),
            _divider("pd_div_haptics"),
            SwitchListTile(
                "Keep screen awake", key="pd_switch_awake",
                control_key="pd_control_awake",
                value=bool(state.keep_awake.value),
                subtitle="Stop the display sleeping while a preview is "
                         "connected.",
                on_change=lambda e: _set_bool(
                    state.keep_awake, "keep_awake", e),
            ),
        ]),
    ])


def _set_bool(target, name: str, event) -> None:
    value = bool(event.value)
    target.value = value
    if name == "keep_awake":
        _apply_keep_awake(value)
    prefs.save(**{name: value})
    refresh()


def _apply_keep_awake(enabled: bool) -> None:
    page = _page()
    if page is None:
        return
    try:
        page.keep_awake(bool(enabled))
    except Exception:
        pass


# ── about ────────────────────────────────────────────────────────────────────


def _about() -> Column:
    _load_device()
    rows = [
        ("Application", f"{APP_NAME} {APP_VERSION}"),
        ("Pydrud framework", PYDRUD_VERSION),
        ("Preview protocol", f"v{PREVIEW_PROTOCOL_VERSION}"),
        ("Renderer protocol", f"v{RENDERER_PROTOCOL_VERSION}"),
        ("Package", PACKAGE),
    ]
    children = [meta_list(rows, key="pd_about_meta")]
    device = _device_rows()
    if device:
        children.append(_divider("pd_div_about"))
        children.append(meta_list(device, key="pd_device_meta"))
    return Column(key="pd_about", spacing=10, children=[
        section_header("About", caption="APP INFO",
                       key="pd_about_section"),
        card(key="pd_about_card", spacing=14, child=children),
    ])


def _load_device() -> None:
    global _device_loaded
    if _device_loaded:
        return
    page = _page()
    if page is None:
        return
    _device_loaded = True
    try:
        page.device.info().then(_on_device_info)
    except Exception:
        pass


def _on_device_info(value: Any) -> None:
    if isinstance(value, dict) and value:
        device_info.value = dict(value)
        refresh()


def _device_rows() -> list:
    info = device_info.value
    if not isinstance(info, dict) or not info:
        return [("Device", "Reading…")]

    rows: list = []
    model = _first(info, "model", "device", "deviceModel")
    maker = _first(info, "manufacturer", "brand", "deviceManufacturer")
    if model:
        label = f"{maker} {model}".strip() if maker else str(model)
        rows.append(("Device", label))

    release = _first(info, "release", "android", "os_version", "osVersion")
    sdk = _first(info, "sdk", "sdk_int", "sdkInt", "api_level", "apiLevel")
    if release or sdk:
        android = str(release or "")
        if sdk:
            android = f"{android} (SDK {sdk})".strip()
        rows.append(("Android", android))

    locale = _first(info, "locale", "language", "country")
    if locale:
        rows.append(("Locale", str(locale)))
    return rows


def _first(info: dict, *names: str):
    for name in names:
        value = info.get(name)
        if value not in (None, ""):
            return value
    return None


# ── links ────────────────────────────────────────────────────────────────────


def _links() -> Column:
    return Column(key="pd_links", spacing=10, children=[
        section_header("Learn more", caption="LINKS",
                       key="pd_links_section"),
        card(key="pd_links_card", spacing=0, child=[
            ListTile("Pydrud documentation", key="pd_link_docs",
                     leading=Icons.BOOKMARK, trailing=Icons.OPEN_IN_NEW,
                     on_click=lambda _e: _open(PYDRUD_DOCS)),
            _divider("pd_div_docs"),
            ListTile("Pydrud on GitHub", key="pd_link_repo",
                     leading=Icons.CODE, trailing=Icons.OPEN_IN_NEW,
                     on_click=lambda _e: _open(PYDRUD_REPO)),
        ]),
    ])


def _open(url: str) -> None:
    page = _page()
    if page is None:
        return
    try:
        page.share.open_url(url)
    except Exception:
        pass


# ── bits ─────────────────────────────────────────────────────────────────────


def _divider(key: str) -> Container:
    return Container(key=key, class_="pd-divider", width="match")


def _footer() -> Container:
    return Container(
        key="pd_settings_footer_box",
        width="match",
        alignment="center",
        child=Text(
            f"{APP_NAME} {APP_VERSION}  ·  Pydrud {PYDRUD_VERSION}",
            key="pd_settings_footer", class_="pd-caption",
        ),
    )


def _page():
    app = current()
    return app.page if app is not None else None
