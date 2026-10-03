"""Reusable application UI components.

The shared vocabulary of Pydash screens: section labels, page scaffolding,
demo cards, metadata rows and monospace code chips. Screens compose these
instead of re-inventing surfaces, which is what keeps the whole app
visually consistent.
"""

from __future__ import annotations

from typing import Callable, Iterable, Optional, Sequence

from pydrud import (
    Card, Colors, Column, Container, Icon, Icons, Radius, Responsive,
    Row, SafeArea, Spacing, Text, Theme, Widget,
)
from pydrud import Center

from app.theme import caption_style, code_style, hairline, pad

__all__ = [
    "CodeChip", "DemoCard", "MetaRow", "MetaList", "page_body", "section",
    "section_header",
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


def section_header(title: str, key: str, subtitle: str = "",
                   icon: str = "") -> Widget:
    """A section header with an icon chip — used to open showcase groups."""
    children: list[Widget] = []
    if icon:
        children.append(Icon(icon, key=f"{key}_icon", size=20,
                             color=Theme.primary))
    children.append(Text(title, key=f"{key}_title", size=16, weight=700,
                         color=Theme.text))
    return Container(
        key=key,
        width="match",
        padding=pad(vertical=Spacing.SM),
        child=Column(
            key=f"{key}_col",
            spacing=2,
            children=[
                Row(key=f"{key}_row", spacing=Spacing.SM,
                    vertical_alignment="center", children=children),
                Text(subtitle, key=f"{key}_sub", size=13,
                     color=Theme.text_secondary) if subtitle else
                Container(key=f"{key}_nosub", height=0),
            ],
        ),
    )


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


def DemoCard(
    key: str,
    *,
    title: str,
    description: str = "",
    icon: str = "",
    badge: Optional[str] = None,
    child: Optional[Widget] = None,
    children: Optional[Iterable[Widget]] = None,
    on_click: Optional[Callable] = None,
    padded: bool = True,
) -> Widget:
    """A showcase card: caption row, live demo content, and a caption.

    ``on_click`` turns the whole card into a tap target (used by the
    component catalog and the playground index).
    """
    body: list[Widget] = []
    if description:
        body.append(Text(description, key=f"{key}_desc", size=13,
                         color=Theme.text_secondary))
    if child is not None:
        body.append(child)
    if children:
        body.extend(children)

    header_children: list[Widget] = []
    if icon:
        header_children.append(Container(
            key=f"{key}_icon_tile",
            width=34,
            height=34,
            border_radius=Radius.SM,
            bg=Colors.with_opacity(Theme.primary, 0.12),
            alignment="center",
            child=Icon(icon, key=f"{key}_icon", size=18,
                       color=Theme.primary),
        ))
    header_children.append(Text(title, key=f"{key}_title", size=15,
                                weight=700, color=Theme.text, expand=1,
                                max_lines=1, overflow="ellipsis"))
    if badge:
        from pydrud import Chip

        header_children.append(Chip(badge, key=f"{key}_badge",
                                    color=Colors.with_opacity(
                                        Theme.primary, 0.10)))

    inner = Column(
        key=f"{key}_body",
        spacing=Spacing.MD,
        children=[
            Row(key=f"{key}_head", spacing=Spacing.SM,
                vertical_alignment="center",
                children=header_children),
            *body,
        ],
    )
    return Card(
        key=key,
        child=inner,
        padding=Spacing.LG if padded else 0,
        on_click=on_click,
    )


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
