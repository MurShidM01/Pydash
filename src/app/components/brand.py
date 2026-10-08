"""The Pydash brand hero — the gradient card at the top of Home.

One widget, one job: introduce the app with its signature gradient and give
the dashboard a strong, recognisable anchor. The gradient comes from
:func:`app.theme.brand_gradient`, so it re-seeds with the palette and reads
correctly in light and dark.
"""

from __future__ import annotations

from typing import Optional

from pydrud import Column, Container, Text, Widget

from app import theme
from app.config import APP_NAME, APP_TAGLINE

__all__ = ["brand_hero"]


def brand_hero(
    *,
    title: str = APP_NAME,
    subtitle: str = APP_TAGLINE,
    caption: str = "PYDRUD LIVE PREVIEW",
    footer: Optional[Widget] = None,
    key: str = "pd_hero",
) -> Container:
    """The brand card: an overline, the wordmark, a tagline and an optional row."""
    children = [
        Text(caption, key=f"{key}_caption", class_="pd-hero-caption",
             max_lines=1),
        Text(title, key=f"{key}_title", class_="pd-hero-title", max_lines=1),
        Text(subtitle, key=f"{key}_sub", class_="pd-hero-sub", max_lines=2),
    ]
    if footer is not None:
        children.append(footer)
    return Container(
        key=key,
        class_="pd-hero",
        width="match",
        style=theme.brand_gradient(),
        child=Column(key=f"{key}_inner", spacing=5, children=children),
    )
