"""Pydash brand identity components.

The visual signature: a gradient tile carrying a bolt-style mark (drawn
natively — no image assets), the Pydash wordmark, and the branded hero
card that anchors the Home screen. Everything is built from ordinary
Pydrud widgets so it reflows, themes and animates with the rest of the app.
"""

from __future__ import annotations

from typing import Optional

from pydrud import (
    Colors, Column, Container, Elevation, Icon, Icons, Radius, Row,
    Spacing, Text, Widget,
)

from app.config import APP_NAME, APP_TAGLINE
from app.theme import brand_gradient, brand_on_surface

__all__ = ["BrandMark", "Wordmark", "BrandHero"]


def BrandMark(key: str, size: float = 44, radius: float = 14) -> Widget:
    """The Pydash glyph: a gradient tile with a white spark mark.

    The mark reads as "live signal" — a spark for speed and energy on top
    of the same indigo→teal gradient the whole app uses.
    """
    inner = size * 0.52
    return Container(
        key=key,
        width=size,
        height=size,
        border_radius=radius,
        alignment="center",
        style=brand_gradient("diagonal"),
        child=Icon(Icons.SPARKLE, key=f"{key}_glyph", size=inner,
                   color=Colors.WHITE),
    )


def Wordmark(key: str, *, size: float = 20,
             color: Optional[str] = None) -> Widget:
    """The Pydash wordmark: heavy 'Py', light 'dash'."""
    base = color or Colors.WHITE
    return Row(
        key=key,
        vertical_alignment="center",
        children=[
            Text("Py", key=f"{key}_py", size=size, weight=800, color=base),
            Text("dash", key=f"{key}_dash", size=size, weight=300,
                 color=base),
        ],
    )


def BrandHero(key: str, subtitle: Optional[str] = None) -> Widget:
    """The branded header card used on the Home screen."""
    return Container(
        key=key,
        width="match",
        border_radius=Radius.XL,
        padding=Spacing.XL,
        style={**brand_gradient("diagonal"), "elevation": Elevation.CARD},
        child=Row(
            key=f"{key}_row",
            spacing=Spacing.LG,
            vertical_alignment="center",
            children=[
                BrandMark(key=f"{key}_mark", size=54, radius=17),
                Column(
                    key=f"{key}_copy",
                    spacing=2,
                    expand=1,
                    children=[
                        Wordmark(key=f"{key}_word", size=26),
                        Text(subtitle or APP_TAGLINE,
                             key=f"{key}_tagline", size=13,
                             color=brand_on_surface(0.85)),
                    ],
                ),
                Icon(Icons.QR_CODE, key=f"{key}_qr", size=22,
                     color=brand_on_surface(0.9)),
            ],
        ),
    )
