"""Reusable application UI components.

The shared vocabulary of Pydash screens: section labels, page scaffolding,
metadata rows and monospace code chips. Screens compose these instead of
re-inventing surfaces, which is what keeps the whole app visually
consistent.
"""

from __future__ import annotations

from typing import Optional, Sequence

from pydrud import (
    Column, Container, Icon, Radius, Responsive, Row, Spacing, Text, Theme,
    Widget,
)
from pydrud import Center

from app.theme import code_style, pad

__all__ = [
    "CodeChip", "MetaRow", "MetaList", "page_body", "section",
]


def section(title: str, key: str, *, subtitle: Optional[str] = None,
            action: Optional[Widget] = None) -> Widget:
    """A quiet, all-caps section label — the spine of a tidy screen."""
    children: list[Widget] = [Text(title.upper(), key=f"{key}_label", size=12,
                                   weight=700, color=Theme.text_secondary,
                                   style={"font": {"letterSpacing": 0.08}})]
    if subtitle:
        children.append(Text(subtitle, key=f"{key}_sub", size=12,
                             color=Theme.text_secondary))
    left = Column(key=f"{key}_text", spacing=2, expand=1, children=children)
    row_children = [left]
    if action is not None:
        row_children.append(action)
    return Container(
        key=key,
        width="match",
        padding=EdgeInsets_section(key),
        child=Row(key=f"{key}_row", vertical_alignment="center",
                  children=row_children),
    )


def EdgeInsets_section(key: str) -> dict:
    from pydrud import EdgeInsets

    return EdgeInsets(left=Spacing.XXS, right=Spacing.XXS,
                      top=Spacing.SM, bottom=Spacing.XXS).to_dict()


def page_body(key: str, children: Sequence[Widget],
              *, vertical_alignment: Optional[str] = None) -> Widget:
    """A scrolling column with a readable, responsive gutter.

    On tablets the content is centred and capped, so text never stretches
    across an ungainly 12-inch line.
    """
    gutter = Responsive.value(phone=Spacing.GUTTER, tablet=Spacing.XXL)
    content = Column(
        key=f"{key}_scroll",
        scroll=True,
        spacing=Spacing.LG,
        vertical_alignment=vertical_alignment,
        style={"padding": _page_padding(gutter)},
        children=list(children),
    )
    if not Responsive.is_tablet():
        return content
    return Center(
        key=f"{key}_center",
        child=Container(key=f"{key}_wrap", width=680, height="match",
                        child=content),
    )


def _page_padding(gutter: float) -> dict:
    from pydrud import EdgeInsets

    return EdgeInsets(left=gutter, right=gutter, top=Spacing.LG,
                      bottom=Spacing.HUGE).to_dict()


def MetaRow(key: str, label: str, value: str,
            *, icon: Optional[str] = None, mono: bool = False) -> Widget:
    """A label/value row for server details and diagnostics."""
    children: list[Widget] = []
    if icon:
        children.append(Icon(icon, key=f"{key}_icon", size=15,
                             color=Theme.text_secondary))
    children.append(Text(label, key=f"{key}_label", size=13,
                         color=Theme.text_secondary, expand=1))
    children.append(Text(
        value, key=f"{key}_value", size=13, weight=600, color=Theme.text,
        text_align="right", max_lines=1, overflow="ellipsis",
        style=code_style() if mono else None,
    ))
    return Row(key=key, spacing=Spacing.SM, vertical_alignment="center",
               children=children)


def MetaList(key: str, rows: Sequence[Widget]) -> Widget:
    """A group of :func:`MetaRow` widgets separated by hairlines."""
    if not rows:
        return Container(key=f"{key}_empty", height=0)
    separated: list[Widget] = []
    for index, row in enumerate(rows):
        if index:
            from pydrud import Divider

            separated.append(Divider(key=f"{key}_div{index}"))
        separated.append(row)
    return Column(key=key, children=separated)


def CodeChip(key: str, text: str, *, full: bool = False) -> Widget:
    """A monospace pill for commands, keys and URIs."""
    return Container(
        key=key,
        width="match" if full else None,
        bg=Theme.surface_variant,
        border_radius=Radius.XS,
        padding=pad(horizontal=Spacing.SM, vertical=Spacing.SM - 2),
        child=Text(
            text, key=f"{key}_text", size=12, color=Theme.text,
            style={"font": {"family": "monospace", "size": 12}},
        ),
    )
