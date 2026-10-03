"""Typography demos — Text, the type-ramp presets, RichText and Markdown."""

from __future__ import annotations

from pydrud import (
    Caption, Colors, Column, Container, Divider, Heading, Label, Link,
    Markdown, Radius, RichText, Row, Slider, Spacing, Span, Subtitle, Text,
    Theme, Title, Widget,
)

from app.runtime import refresh
from app.state import State

__all__ = ["CATEGORY"]

#: Live type-scale factor for the ramp demo.
scale = State(1.0, name="type_scale")


def _ramp(key: str) -> Widget:
    factor = max(0.8, min(float(scale.value), 1.6))
    rows = (
        ("Heading", lambda: Heading("Display heading", size=int(34 * factor))),
        ("Title", lambda: Title("Screen title", size=int(22 * factor))),
        ("Subtitle", lambda: Subtitle("Supporting subtitle",
                                      size=int(16 * factor))),
        ("Label", lambda: Label("Section label", size=int(14 * factor))),
        ("Caption", lambda: Caption("Quiet caption", size=int(12 * factor))),
        ("Body", lambda: Text(
            "Body copy in the default weight, wrapping naturally across "
            "lines so you can judge line height and rhythm.",
            size=int(15 * factor), color=Theme.text)),
    )
    children: list[Widget] = []
    for index, (name, make) in enumerate(rows):
        if index:
            children.append(Divider(key=f"{key}_div{index}"))
        children.append(Row(
            key=f"{key}_row{index}",
            spacing=Spacing.LG,
            vertical_alignment="center",
            children=[
                Text(name.upper(), key=f"{key}_tag{index}", size=10,
                     weight=700, color=Theme.text_secondary, expand=1,
                     style={"font": {"letterSpacing": 0.08}}),
                Container(
                    key=f"{key}_sample{index}",
                    width=230,
                    child=make(),
                ),
            ],
        ))
    return Column(key=f"{key}_col", spacing=Spacing.SM, children=children)


def _weights(key: str) -> Widget:
    weights = (300, 400, 500, 600, 700, 800)
    return Column(
        key=f"{key}_col",
        spacing=Spacing.XS,
        children=[
            Text("Aa", key=f"{key}_w{w}", size=26, weight=w,
                 color=Theme.text) for w in weights
        ],
    )


def _rich(key: str) -> Widget:
    return RichText(
        [
            Span("Pydrud renders ", size=14),
            Span("mixed styles", size=14, weight=700, color=Theme.primary),
            Span(" inside one native TextView — ", size=14),
            Span("bold", size=14, weight=700),
            Span(", ", size=14),
            Span("italic", size=14, italic=True),
            Span(", ", size=14),
            Span("strikethrough", size=14, strike=True),
            Span(", ", size=14),
            Span("highlighted", size=14, bg=Colors.with_opacity(
                Theme.primary, 0.14)),
            Span(" and ", size=14),
            Span("tappable links", size=14, link="pydash://components",
                 color=Theme.primary),
            Span(".", size=14),
        ],
        key=f"{key}_rich",
        on_link=lambda e: None,
    )


_MD_SOURCE = """## Markdown, parsed in Python

A **pragmatic subset** — headings, lists, code, links and emphasis —
rendered as *native* text blocks, not a WebView.

- Declarative source, styled output
- `inline code` and fenced blocks

```python
Markdown("# Hello from Pydrud")
```

[Pydrud on GitHub](https://github.com/MurShidM01/Pydrud)
"""


def _markdown(key: str) -> Widget:
    return Container(
        key=f"{key}_wrap",
        border_radius=Radius.MD,
        padding=Spacing.MD,
        bg=Theme.surface_variant,
        child=Markdown(_MD_SOURCE, key=f"{key}_md", size=13),
    )


def _align(key: str) -> Widget:
    return Column(
        key=f"{key}_align_col",
        spacing=Spacing.XS,
        children=[
            Text("Left aligned", key=f"{key}_l", size=13,
                 color=Theme.text),
            Text("Centered", key=f"{key}_c", size=13, text_align="center",
                 color=Theme.text),
            Text("Right aligned", key=f"{key}_r", size=13, text_align="right",
                 color=Theme.text),
            Link("A themed inline link", key=f"{key}_link", size=13),
        ],
    )


def _set_scale(event) -> None:
    try:
        scale.value = float(event.get("value", 1.0))
    except (TypeError, ValueError):
        return
    refresh()


def build_ramp(key: str) -> Widget:
    return Column(
        key=f"{key}_body",
        spacing=Spacing.MD,
        children=[
            _ramp(key),
            Text(f"Type scale ×{float(scale.value):.2f}",
                 key=f"{key}_scale_label", size=12, weight=600,
                 color=Theme.primary),
            Slider(float(scale.value), key=f"{key}_scale_slider",
                   min=0.8, max=1.6).on_change(_set_scale),
        ],
    )


from app.data.catalog import Category, Demo  # noqa: E402

CATEGORY = Category(
    id="typography",
    name="Typography",
    icon="edit",
    blurb="The type ramp, weights, rich text and Markdown — all native.",
    demos=(
        Demo(id="ramp", title="Type ramp",
             description="Every step of the Material scale; drag to preview "
                         "accessibility scaling.",
             build=build_ramp,
             tags=("text", "heading", "title", "label", "caption")),
        Demo(id="weights", title="Weights & alignment",
             description="Font weights 300–800 and text alignment options.",
             build=lambda key: Column(
                 key=f"{key}_body", spacing=Spacing.LG,
                 children=[_weights(key), Divider(key=f"{key}_div"),
                           _align(key)]),
             tags=("weight", "align", "link")),
        Demo(id="rich", title="RichText spans",
             description="Multiple styles and links inside a single TextView.",
             build=lambda key: _rich(key), tags=("span", "link", "richtext")),
        Demo(id="markdown", title="Markdown",
             description="Headings, lists, code and emphasis — parsed in "
                         "Python, rendered natively.",
             build=lambda key: _markdown(key), tags=("md", "code", "docs")),
    ),
)
