"""Scan — camera QR capture plus manual connection entry.

The primary flow is the camera: a live ``CameraPreview`` with ML Kit QR
scanning enabled, which hands the raw payload straight to
:func:`app.preview.uri.parse_preview_uri`. Manual entry covers no-camera
devices and stubborn terminals: paste the URI the dev server prints (or
type host/port/session/token), and Pydash validates it with the same
rules the server applies.
"""

from __future__ import annotations

from typing import Optional

from pydrud import (
    Button, Card, Column, Container, Divider, Icon, Icons, Radius, Row,
    SegmentedButton, Spacing, Switch, Text, TextField, Theme, Widget,
)

from app.components import section
from app.config import APP_VERSION, DEFAULT_PREVIEW_PORT
from app.preview.models import Endpoint
from app.preview.session import session
from app.preview.uri import (
    PreviewUriError, normalise_uri, parse_preview_uri,
)
from app.runtime import current, refresh, router
from app.state import State

__all__ = ["scan_screen"]

#: Screen state (scoped to this screen's lifetime).
manual_mode = State(False, name="scan_manual")
camera_state = State("unknown", name="scan_camera")  # unknown|granted|denied
uri_text = State("", name="scan_uri")
host_text = State("", name="scan_host")
port_text = State(str(DEFAULT_PREVIEW_PORT), name="scan_port")
session_text = State("", name="scan_session")
token_text = State("", name="scan_token")
notice = State("", name="scan_notice")
notice_kind = State("error", name="scan_notice_kind")
scanning = State(False, name="scan_scanning")


def scan_screen(page, params=None) -> None:
    params = dict(params or {})
    mode = params.get("mode")
    if mode == "manual" or bool(params.get("uri")):
        manual_mode.value = True
        if params.get("uri"):
            uri_text.value = str(params["uri"])
    else:
        manual_mode.value = False

    notice.value = ""
    scanning.value = False

    page.bgcolor = Theme.background
    page.add(Container(
        key="pd_scan_root",
        width="match",
        height="match",
        child=_screen(),
    ))

    if not manual_mode.value and camera_state.value == "unknown":
        _request_camera()


def _screen() -> Widget:
    from app.components import page_body

    children: list[Widget] = [_header(), _mode_toggle()]
    if manual_mode.value:
        children.append(_manual_card())
    else:
        children.append(_camera_card())
        children.append(_manual_link())
    return page_body("pd_scan", children)


def _header() -> Widget:
    return Row(
        key="pd_scan_header",
        spacing=Spacing.MD,
        vertical_alignment="center",
        children=[
            Icon(Icons.CHEVRON_LEFT, key="pd_scan_back", size=22,
                 color=Theme.text).on_click(lambda _e: router.pop()),
            Column(
                key="pd_scan_header_col",
                spacing=2,
                expand=1,
                children=[
                    Text("Connect to a dev server",
                         key="pd_scan_title", size=18, weight=700,
                         color=Theme.text),
                    Text("Scan the QR code printed by `pydrud dev`",
                         key="pd_scan_sub", size=12,
                         color=Theme.text_secondary),
                ],
            ),
        ],
    )


def _mode_toggle() -> Widget:
    return SegmentedButton(
        ["Scan QR code", "Enter manually"],
        key="pd_scan_mode_toggle",
        selected=1 if manual_mode.value else 0,
    ).on_change(_on_mode_change)


def _on_mode_change(event) -> None:
    val = 0
    if isinstance(event, dict):
        val = event.get("value", 0)
    elif hasattr(event, "value"):
        val = getattr(event, "value", 0)
    try:
        val = int(val)
    except (TypeError, ValueError):
        val = 0

    if val == 1:
        _switch_manual()
    else:
        _switch_camera()


# ── camera ──────────────────────────────────────────────────────────────────

def _camera_card() -> Widget:
    granted = camera_state.value == "granted"
    if granted:
        from pydrud import CameraPreview

        camera = CameraPreview(
            key="pd_scan_camera",
            facing="back",
            fit="cover",
            scan=True,
            scan_formats=("QR_CODE",),
            scan_overlay=True,
            on_scan=_on_scan,
            on_error=lambda e: _fail("Camera error: "
                                     + str(getattr(e, "data", {}).get(
                                         "message", "unknown"))),
        )
        preview: Widget = Container(
            key="pd_scan_camera_wrap",
            width="match",
            border_radius=Radius.LG,
            style={"border": {"color": Theme.outline, "width": 1}},
            child=camera,
        )
        note = ("Point at the terminal. Pydash reads the code the moment "
                "it is in frame.", "ok")
    elif camera_state.value == "denied":
        preview = _denied_pane()
        note = ("Camera permission denied — use manual entry below.",
                "error")
    else:
        preview = Container(
            key="pd_scan_camera_pending",
            width="match",
            height=260,
            border_radius=Radius.LG,
            bg=Theme.surface_variant,
            alignment="center",
            child=Column(
                key="pd_scan_pending_col",
                spacing=Spacing.SM,
                horizontal_alignment="center",
                children=[
                    Icon(Icons.CAMERA, key="pd_scan_pending_icon", size=30,
                         color=Theme.text_secondary),
                    Text("Waiting for camera permission…",
                         key="pd_scan_pending_t", size=13,
                         color=Theme.text_secondary),
                ],
            ),
        )
        note = ("Pydash asks for the camera once, only to read QR codes.",
                "info")

    children: list[Widget] = [preview]
    if notice.value:
        children.append(_notice())
    children.append(Text(note[0], key="pd_scan_camera_note", size=12,
                         color=Theme.text_secondary, text_align="center"))
    if camera_state.value == "denied":
        children.append(Button("Enter connection manually",
                               key="pd_scan_switch_manual", variant="tonal",
                               icon=Icons.EDIT, full_width=True
                               ).on_click(lambda _e: _switch_manual()))
    return Card(key="pd_scan_camera_card", padding=Spacing.LG,
                child=Column(key="pd_scan_camera_col", spacing=Spacing.MD,
                             children=children))


def _denied_pane() -> Widget:
    return Container(
        key="pd_scan_denied",
        width="match",
        height=200,
        border_radius=Radius.LG,
        bg=Theme.surface_variant,
        alignment="center",
        child=Column(
            key="pd_scan_denied_col",
            spacing=Spacing.SM,
            horizontal_alignment="center",
            children=[
                Icon(Icons.VISIBILITY_OFF, key="pd_scan_denied_icon",
                     size=30, color=Theme.text_secondary),
                Text("Camera unavailable", key="pd_scan_denied_t", size=14,
                     weight=600, color=Theme.text),
                Button("Try again", key="pd_scan_retry_cam", variant="tonal",
                       size="sm", icon=Icons.REFRESH
                       ).on_click(lambda _e: _request_camera()),
            ],
        ),
    )


def _manual_link() -> Widget:
    return Button("Enter connection details manually",
                  key="pd_scan_manual_link", variant="text",
                  icon=Icons.KEYBOARD if hasattr(Icons, "KEYBOARD")
                  else Icons.EDIT,
                  ).on_click(lambda _e: _switch_manual())


def _switch_manual() -> None:
    manual_mode.value = True
    notice.value = ""
    router.replace("scan", mode="manual")


def _switch_camera() -> None:
    manual_mode.value = False
    notice.value = ""
    if camera_state.value == "unknown":
        _request_camera()
    router.replace("scan", mode="scan")


# ── manual entry ────────────────────────────────────────────────────────────

def _manual_card() -> Widget:
    children: list[Widget] = [
        section("Paste the connection URI", "pd_scan_uri_sec"),
        TextField(uri_text.value, key="pd_scan_uri_field",
                  hint="pydrud://preview/connect?host=…",
                  ime_action="go",
                  on_submit=lambda _e: _connect_uri(),
                  ).on_change(_set_uri),
        Button("Connect", key="pd_scan_uri_connect", icon=Icons.LINK,
               full_width=True,
               disabled=not uri_text.value.strip()
               ).on_click(lambda _e: _connect_uri()),
    ]
    if notice.value:
        children.append(_notice())
    children.extend([
        Row(
            key="pd_scan_or_row",
            spacing=Spacing.MD,
            vertical_alignment="center",
            children=[
                Divider(key="pd_scan_or_div", expand=1),
                Text("OR", key="pd_scan_or", size=11, weight=700,
                     color=Theme.text_secondary),
                Divider(key="pd_scan_or_div2", expand=1),
            ],
        ),
        section("Enter the parts", "pd_scan_parts_sec"),
        TextField(host_text.value, key="pd_scan_host", hint="192.168.1.20",
                  label="Host", keyboard="url", ime_action="next").on_change(_set_host),
        TextField(port_text.value, key="pd_scan_port", hint="8597",
                  label="Port", keyboard="number", ime_action="next").on_change(_set_port),
        TextField(session_text.value, key="pd_scan_session",
                  label="Session id", ime_action="next").on_change(_set_session),
        TextField(token_text.value, key="pd_scan_token", label="Token",
                  password=True, ime_action="done",
                  on_submit=lambda _e: _connect_parts()).on_change(_set_token),
        Button("Connect", key="pd_scan_parts_connect",
               icon=Icons.LINK, full_width=True,
               ).on_click(lambda _e: _connect_parts()),
        _recent(),
        Button("Scan QR code with camera",
               key="pd_scan_switch_camera", variant="tonal",
               icon=Icons.CAMERA, full_width=True
               ).on_click(lambda _e: _switch_camera()),
    ])
    return Card(
        key="pd_scan_manual_card",
        padding=Spacing.LG,
        child=Column(key="pd_scan_manual_col", spacing=Spacing.MD,
                     children=children),
    )


def _recent() -> Widget:
    stored = session.endpoint
    if stored is None:
        stored = _stored_endpoint()
    if stored is None:
        return Container(key="pd_scan_no_recent", height=0)
    return Column(
        key="pd_scan_recent",
        spacing=Spacing.SM,
        children=[
            Divider(key="pd_scan_recent_div"),
            Text("Last session", key="pd_scan_recent_label", size=12,
                 weight=700, color=Theme.text_secondary,
                 style={"font": {"letterSpacing": 0.08}}),
            Button(f"Reconnect to {stored.describe()}",
                   key="pd_scan_reconnect", variant="outlined", size="sm",
                   icon=Icons.SYNC).on_click(
                       lambda _e: _connect_endpoint(stored)),
        ],
    )


def _stored_endpoint() -> Optional[Endpoint]:
    from app.state import last_endpoint

    stored = last_endpoint.value
    if not isinstance(stored, dict) or not stored.get("session_id"):
        return None
    try:
        return Endpoint(
            host=str(stored.get("host", "")),
            port=int(stored.get("port", 0) or 0),
            session_id=str(stored["session_id"]),
            token=str(stored.get("token", "")),
            project_id=str(stored.get("project_id", "")),
            project_name=str(stored.get("project_name", "")),
        )
    except (TypeError, ValueError):
        return None


def _set_uri(event):
    uri_text.value = normalise_uri(str(event.get("value", "")))
    refresh()


def _set_host(event):
    host_text.value = str(event.get("value", ""))
    refresh()


def _set_port(event):
    port_text.value = str(event.get("value", ""))
    refresh()


def _set_session(event):
    session_text.value = str(event.get("value", ""))
    refresh()


def _set_token(event):
    token_text.value = str(event.get("value", ""))
    refresh()


def _notice() -> Widget:
    color = (Theme.error if notice_kind.value == "error"
             else Theme.primary)
    return Container(
        key="pd_scan_notice",
        width="match",
        border_radius=Radius.MD,
        padding=Spacing.MD,
        bg=Theme.surface_variant,
        child=Row(
            key="pd_scan_notice_row",
            spacing=Spacing.SM,
            vertical_alignment="center",
            children=[
                Icon(Icons.WARNING if notice_kind.value == "error"
                     else Icons.INFO, key="pd_scan_notice_icon", size=16,
                     color=color),
                Text(notice.value, key="pd_scan_notice_text", size=12,
                     color=color, expand=1),
            ],
        ),
    )


# ── connecting ──────────────────────────────────────────────────────────────

def _request_camera() -> None:
    page = _page()
    if page is None or not hasattr(page, "permissions"):
        camera_state.value = "denied"
        return

    def done(result=None):
        granted = False
        if isinstance(result, dict):
            granted = bool(
                result.get("android.permission.CAMERA")
                or result.get("camera")
                or any(result.values())
            )
        elif isinstance(result, bool):
            granted = result
        elif result is not None:
            granted = bool(result)
        camera_state.value = "granted" if granted else "denied"
        refresh()

    try:
        page.permissions.request("camera").then(done).catch(lambda _error: done(False))
    except Exception:
        done(False)


def _on_scan(event) -> None:
    data = getattr(event, "data", None) or {}
    payload = str(data.get("value", "") or data.get("raw", "") or "")
    if not payload or scanning.value:
        return
    scanning.value = True
    try:
        target = parse_preview_uri(normalise_uri(payload))
    except PreviewUriError as exc:
        _fail(exc.message)
        return
    finally:
        scanning.value = False
    _connect_target(target)


def _connect_uri() -> None:
    text = normalise_uri(uri_text.value)
    try:
        target = parse_preview_uri(text)
    except PreviewUriError as exc:
        _fail(exc.message)
        return
    _connect_target(target)


def _connect_parts() -> None:
    host = host_text.value.strip()
    session_id = session_text.value.strip()
    token = token_text.value.strip()
    if not host or not session_id or not token:
        _fail("Host, session and token are all required.")
        return
    try:
        port = int(port_text.value.strip() or DEFAULT_PREVIEW_PORT)
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        _fail("Port must be a number between 1 and 65535.")
        return
    _connect_endpoint(Endpoint(
        host=host, port=port, session_id=session_id, token=token))


def _connect_target(target) -> None:
    _connect_endpoint(Endpoint(
        host=target.host, port=target.port,
        session_id=target.session_id, token=target.token,
        project_id=target.project_id,
        project_name=target.project_name))


def _connect_endpoint(endpoint: Endpoint) -> None:
    notice.value = ""
    uri_text.value = ""
    session.connect(endpoint)
    router.replace("preview")


def _fail(message: str) -> None:
    notice.value = message
    notice_kind.value = "error"
    refresh()


def _page():
    app = current()
    return app.page if app is not None else None
