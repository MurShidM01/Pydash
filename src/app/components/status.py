"""Connection-status indicators shared by every Pydash screen.

Two tiny widgets — a dot and a pill — driven by the one colour system in
:mod:`app.theme`. Both default to the *live* preview session state, so a
screen only has to call ``status_pill()`` and it stays in sync with whatever
:mod:`app.preview.session` is doing.

The pill is also the compact status readout the preview header shows while a
project is rendering, so its label comes straight from the shared
``STATE_LABELS`` vocabulary rather than being invented per screen.
"""

from __future__ import annotations

from typing import Optional

from pydrud import Container, Row, Text

from app import theme
from app.preview.models import STATE_LABELS
from app.preview.session import session

__all__ = ["status_dot", "status_pill"]


def status_dot(state: Optional[str] = None, *, size: float = 9,
               key: str = "pd_status_dot") -> Container:
    """A small filled circle in the colour of *state* (default: live)."""
    current = state or session.state
    return Container(
        key=key,
        class_="pd-dot",
        style={"width": size, "height": size, "bg": theme.status_color(current)},
    )


def status_pill(state: Optional[str] = None, *,
                key: str = "pd_status_pill") -> Container:
    """A tinted capsule: a status dot plus the friendly state label."""
    current = state or session.state
    color = theme.status_color(current)
    label = STATE_LABELS.get(current, "Preview")
    return Container(
        key=key,
        class_="pd-pill",
        style={"bg": theme.status_surface(current)},
        child=Row(
            key=f"{key}_row",
            spacing=6,
            main_axis_size="min",
            vertical_alignment="center",
            children=[
                status_dot(current, size=8, key=f"{key}_dot"),
                Text(label, key=f"{key}_text", class_="pd-pill-text",
                     style={"color": color}, max_lines=1, overflow="clip"),
            ],
        ),
    )
