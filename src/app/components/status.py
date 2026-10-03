"""Connection status primitives.

One visual language for connection state everywhere in Pydash: a coloured
dot, a labelled pill, and a revision chip. The colours come from
:mod:`app.theme`'s status system so dashboards, headers and preview chrome
all agree.
"""

from __future__ import annotations

from typing import Optional

from pydrud import (
    Colors, Container, Icon, Icons, Radius, Row, Spacing, Text, Widget,
)

from app.preview.models import STATE_HINTS, STATE_LABELS, ConnectionState
from app.theme import pad, status_color, status_surface

__all__ = ["StatusDot", "StatusPill", "RevisionChip"]


def StatusDot(key: str, state: str, size: float = 9) -> Widget:
    """A small circular state indicator."""
    return Container(
        key=key,
        width=size,
        height=size,
        border_radius=Radius.PILL,
        bg=status_color(state),
    )


def StatusPill(key: str, state: str, *, label: Optional[str] = None,
               error: Optional[str] = None) -> Widget:
    """The labelled status badge used on cards and headers.

    For failed states the pill grows a small warning glyph — failures
    deserve slightly more attention than a plain colour change.
    """
    text = label or STATE_LABELS.get(state, state)
    failed = state == ConnectionState.FAILED
    children = [StatusDot(key=f"{key}_dot", state=state)]
    if failed:
        children.append(Icon(Icons.WARNING, key=f"{key}_warn", size=13,
                             color=status_color(state)))
    children.append(Text(
        text, key=f"{key}_label", size=12, weight=600,
        color=status_color(state),
    ))
    return Container(
        key=key,
        bg=status_surface(state),
        border_radius=Radius.PILL,
        padding=pad(horizontal=Spacing.MD + 2, vertical=Spacing.XS + 2),
        child=Row(
            key=f"{key}_row",
            spacing=Spacing.XS + 2,
            vertical_alignment="center",
            children=children,
        ),
    )


def RevisionChip(key: str, revision: int) -> Widget:
    """Monospace revision counter shown while previewing."""
    return Container(
        key=key,
        border_radius=Radius.PILL,
        bg=Colors.with_opacity(Colors.WHITE, 0.16),
        padding=pad(horizontal=Spacing.SM, vertical=Spacing.XS),
        child=Text(
            f"rev {revision}" if revision else "rev —",
            key=f"{key}_label", size=11, weight=600, color=Colors.WHITE,
            style={"font": {"family": "monospace"}},
        ),
    )
