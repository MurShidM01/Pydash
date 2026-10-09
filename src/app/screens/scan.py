"""Scan — get a connection, two ways.

A pushed route with a ``mode`` parameter:

* ``mode="scan"``   — a live CameraX QR reader with the native focus frame;
* ``mode="manual"`` — a field for pasting the connection URL printed by
  ``pydrud dev``.

Both paths end in the same place: the payload is validated with
:func:`app.preview.uri.parse_preview_uri` (the client-side mirror of the host
contract), an :class:`~app.preview.models.Endpoint` is built, and the session is
started through :func:`app.connection.start`. The screen then shows a spinner
while the handshake runs and only swaps itself for the preview once the link is
up — so the user never lands on an empty stage wondering whether it worked.
Validation errors are shown inline rather than as a toast, so the message stays
on screen while the user corrects the input.
"""

from __future__ import annotations

from typing import Any, Optional

from pydrud import (
    BackButton,
    Button,
    Column,
    Container,
    Icons,
    OutlinedButton,
    QRScanner,
    Row,
    Scaffold,
    State,
    Text,
    TextField,
)

from app import connection, state, theme
from app.components import (
    app_bar,
    card,
    loading_panel,
    notice_state,
    section_header,
)
from app.preview import session
from app.preview.models import STATE_HINTS, Endpoint
from app.preview.uri import PreviewUriError, normalise_uri, parse_preview_uri
from app.runtime import current, refresh, router

__all__ = ["scan_screen", "manual_text", "scan_error"]

#: The text currently in the manual-entry field. A ``State`` so it survives
#: the rebuilds the router triggers (and the framework's stateful hot reload).
manual_text = State("", name="pd_manual_text")

#: The last validation message, shown above the input until it is corrected.
scan_error = State("", name="pd_scan_error")


def scan_screen(page, params: Optional[dict] = None) -> None:
    """Route builder: the scan-or-paste screen."""
    mode = "manual" if (params or {}).get("mode") == "manual" else "scan"
    page.add(Scaffold(
        key="pd_scan",
        class_="pd-screen",
        bg_color=theme.background(),
        app_bar=app_bar(
            "Scan QR code" if mode == "scan" else "Connection URL",
            leading=BackButton(on_click=lambda _e: router.pop(), size="sm"),
            key="pd_scan_bar",
        ),
        body=Column(
            key="pd_scan_body",
            class_="pd-screen",
            scroll=True,
            spacing=18,
            style={"padding": theme.page_insets(top=14, bottom=28)},
            children=_children(mode),
        ),
    ))
    dialog = connection.failure_dialog()
    if dialog is not None:
        page.add_floating(dialog)


# ── layout ───────────────────────────────────────────────────────────────────


def _children(mode: str) -> list:
    # While the handshake is running the whole screen becomes one spinner: the
    # camera is released (no QRScanner in the tree) and no control can start a
    # second connection.
    if state.connecting.value:
        return [_connecting_panel()]

    children: list = []

    if scan_error.value:
        children.append(notice_state(
            Icons.ERROR, "That code didn't work", scan_error.value,
            key="pd_scan_error", tone="danger",
        ))

    if mode == "scan":
        children.append(_camera_card())
        children.append(Text(
            "Point the camera at the QR code shown by `pydrud dev`.",
            key="pd_scan_hint", class_="pd-body", text_align="center",
        ))
        children.append(OutlinedButton(
            "Enter the URL manually", icon=Icons.LINK, full_width=True,
            on_click=lambda _e: _switch("manual"),
        ))
    else:
        children.append(_manual_card())
        children.append(OutlinedButton(
            "Scan a QR code instead", icon=Icons.QR_CODE, full_width=True,
            on_click=lambda _e: _switch("scan"),
        ))

    children.append(_tip_card())
    return children


def _connecting_panel() -> Column:
    endpoint = state.connecting_endpoint.value
    host = ""
    if isinstance(endpoint, dict):
        host = f"{endpoint.get('host', '')}:{endpoint.get('port', '')}"
    label = STATE_HINTS.get(session.state, "Reaching the development server…")
    return Column(
        key="pd_scan_connecting",
        spacing=10,
        children=[
            loading_panel(
                "Connecting…",
                f"{host}\n{label}" if host else label,
                key="pd_scan_connecting_panel",
            ),
            OutlinedButton(
                "Cancel", icon=Icons.CLOSE, full_width=True,
                on_click=lambda _e: connection.cancel(),
            ),
        ],
    )


def _camera_card() -> Container:
    return Container(
        key="pd_camera_wrap",
        width="match",
        style={"borderRadius": 20, "bg": "#FF000000"},
        child=QRScanner(
            key="pd_scanner",
            height=340,
            style={"borderRadius": 20, "width": "match"},
            on_scan=_on_scan,
            fallback=_camera_fallback(),
        ),
    )


def _camera_fallback() -> Container:
    return notice_state(
        Icons.CAMERA, "Camera unavailable",
        "Allow camera access for Pydash in Android Settings, or enter the "
        "connection URL by hand.",
        key="pd_camera_fallback", tone="warning",
    )


def _manual_card() -> Container:
    return card(key="pd_manual_card", spacing=12, child=[
        section_header("Connection URL", caption="PASTED FROM THE TERMINAL"),
        TextField(
            key="pd_manual_field",
            value=manual_text.value,
            label="Preview URL",
            hint="pydrud://preview/connect?host=…&port=…&session=…&token=…",
            icon=Icons.LINK,
            keyboard="url",
            ime_action="go",
            on_change=_on_manual_change,
            on_submit=lambda _e: _connect_manual(),
        ),
        Button("Connect", icon=Icons.ARROW_FORWARD, full_width=True, size="lg",
               on_click=lambda _e: _connect_manual()),
        # A full-width box with a content-sized row centred inside it — the
        # reliable way to centre in this layout engine (a Row's own
        # horizontal alignment does not centre natively).
        Container(
            key="pd_manual_aux",
            width="match",
            alignment="center",
            child=Row(
                key="pd_manual_aux_row",
                spacing=10,
                main_axis_size="min",
                children=[
                    OutlinedButton("Paste", icon=Icons.PASTE,
                                   on_click=lambda _e: _paste()),
                    OutlinedButton("Clear", icon=Icons.CLOSE,
                                   on_click=lambda _e: _clear()),
                ],
            ),
        ),
    ])


def _tip_card() -> Container:
    return card(key="pd_tip_card", tint=True, spacing=8, child=[
        Row(
            key="pd_tip_head",
            spacing=8,
            main_axis_size="min",
            vertical_alignment="center",
            children=[
                Text("💡", key="pd_tip_glyph", size=15),
                Text("Where to find it", key="pd_tip_title",
                     class_="pd-meta-val"),
            ],
        ),
        Text(
            "`pydrud dev` prints the address, the one-run key and the QR "
            "code. Both devices must be on the same Wi-Fi network.",
            key="pd_tip_body", class_="pd-body",
        ),
    ])


# ── actions ──────────────────────────────────────────────────────────────────


def _switch(mode: str) -> None:
    scan_error.value = ""
    router.replace("scan", mode=mode)


def _on_manual_change(event) -> None:
    manual_text.value = str(event.value or "")
    if scan_error.value:
        scan_error.value = ""


def _on_scan(event) -> None:
    """A QR code was decoded by the camera."""
    if state.connecting.value or session.is_busy or session.is_live:
        return
    value = ""
    try:
        value = str(event.data.get("value") or "")
    except Exception:
        value = ""
    if value:
        _connect(value)


def _connect_manual() -> None:
    _connect(manual_text.value)


def _connect(text: str) -> None:
    if state.connecting.value or session.is_busy or session.is_live:
        return
    try:
        target = parse_preview_uri(normalise_uri(text))
    except PreviewUriError as exc:
        scan_error.value = exc.message
        refresh()
        return

    scan_error.value = ""
    endpoint = Endpoint(
        host=target.host,
        port=target.port,
        session_id=target.session_id,
        token=target.token,
        project_id=target.project_id,
        project_name=target.project_name,
    )
    # The screen stays put and spins; `app.connection` swaps it for the preview
    # (replace, not push — leaving the preview must never return to a scanner
    # still holding the camera open) once the handshake lands.
    connection.start(endpoint, origin="scan")


def _paste() -> None:
    page = _page()
    if page is None:
        return
    try:
        page.clipboard.paste().then(_on_pasted)
    except Exception:
        pass


def _on_pasted(value: Any) -> None:
    if isinstance(value, str) and value.strip():
        manual_text.value = value.strip()
        scan_error.value = ""
        refresh()


def _clear() -> None:
    manual_text.value = ""
    scan_error.value = ""
    refresh()


def _page():
    app = current()
    return app.page if app is not None else None
