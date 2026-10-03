"""Canvas, chart and media demos — custom drawing and data visuals."""

from __future__ import annotations

import math

from pydrud import (
    Border, Button, Canvas, Chart, CircleImage, Colors, Column, Container,
    Icon, Icons, Markdown, NetworkImage, Radius, Row, Spacing, Text,
    Theme, Widget,
)

from app.runtime import refresh
from app.state import State

__all__ = ["CATEGORY"]

#: Interactive state.
points = State((12, 18, 14, 26, 22, 34, 30, 41), name="viz_points")
kind = State("line", name="viz_kind")

KINDS = ("line", "bar", "area", "pie")


def _signal(key: str) -> Widget:
    """A custom Canvas composition: rings, a sparkline and labels."""
    values = points.value

    def draw(canvas: Canvas):
        (canvas
         .circle(0.5, 0.5, 0.44, color=Colors.with_opacity(Theme.primary, 0.10),
                 fill=True)
         .circle(0.5, 0.5, 0.30, color=Colors.with_opacity(Theme.secondary, 0.14),
                 fill=True)
         .circle(0.5, 0.5, 0.16, color=Colors.with_opacity(Theme.primary, 0.2),
                 fill=True))
        # A live "signal" line across the composition.
        path = []
        for index in range(24):
            x = index / 23
            y = 0.5 + 0.34 * math.sin(index * 0.55) * math.cos(index * 0.21)
            path.append((x, y))
        from pydrud import Path

        canvas.path(Path().smooth(path), color=Theme.primary, width=2.5)
        canvas.circle(1.0, 0.5 + 0.34 * math.sin(23 * 0.55) * math.cos(23 * 0.21),
                      0.03, color=Theme.secondary, fill=True)
        canvas.text("LIVE", 0.5, 0.06, size=11, weight=800,
                    color=Colors.with_opacity(Theme.primary, 0.9),
                    align="center")

    return Canvas(
        key=f"{key}_canvas",
        width="match",
        height=210,
        bg=Theme.surface_variant,
        on_draw=draw,
    )


def _sparkline(key: str) -> Widget:
    def draw(canvas: Canvas):
        canvas.sparkline(points.value, color=Theme.primary, width=2.5,
                         fill=True)
        low, high = min(points.value), max(points.value)
        canvas.text(f"low {low}", 0.02, 0.12, size=10,
                    color=Theme.text_secondary)
        canvas.text(f"high {high}", 0.98, 0.12, size=10, weight=700,
                    color=Theme.primary, align="right")

    return Canvas(key=f"{key}_canvas", width="match", height=90,
                  bg=Theme.surface_variant, on_draw=draw)


def _charts(key: str) -> Widget:
    labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    values = list(points.value)[-7:]
    if len(values) < 7:
        values = (values + [0] * 7)[:7]
    if kind.value == "pie":
        values = values[:5]
        labels = labels[:5]
    return Column(
        key=f"{key}_col",
        spacing=Spacing.MD,
        children=[
            Chart(values, key=f"{key}_chart", kind=kind.value, labels=labels,
                  height=190, show_grid=kind.value in ("line", "bar"),
                  show_values=kind.value == "bar"),
            Row(key=f"{key}_kinds", spacing=Spacing.XS,
                horizontal_alignment="center", children=[
                    Button(k, key=f"{key}_kind_{k}", variant=
                           "filled" if kind.value == k else "outlined",
                           size="sm").on_click(_pick_kind(k))
                    for k in KINDS
                ]),
        ],
    )


def _pick_kind(choice: str):
    def handler(_event):
        kind.value = choice
        refresh()
    return handler


def _shuffle(_event):
    import random

    base = [random.randint(8, 44) for _ in range(8)]
    points.value = tuple(base)
    refresh()


def _images(key: str) -> Widget:
    return Column(
        key=f"{key}_col",
        spacing=Spacing.MD,
        children=[
            Row(key=f"{key}_row", spacing=Spacing.MD,
                horizontal_alignment="center", children=[
                    NetworkImage(
                        "https://picsum.photos/seed/pydash/200/200",
                        key=f"{key}_net", width=96, height=96,
                        border_radius=Radius.MD),
                    CircleImage(
                        "https://picsum.photos/seed/pydrud/200/200",
                        key=f"{key}_circle", size=96),
                    Container(
                        key=f"{key}_ph",
                        width=96,
                        height=96,
                        border_radius=Radius.MD,
                        border=Theme.outline,
                        alignment="center",
                        child=Icon(Icons.IMAGE, key=f"{key}_ph_icon", size=26,
                                   color=Theme.text_secondary),
                    ),
                ]),
            Text("NetworkImage, CircleImage and a local placeholder tile.",
                 key=f"{key}_note", size=12,
                 color=Theme.text_secondary, text_align="center"),
        ],
    )


from app.data.catalog import Category, Demo  # noqa: E402

CATEGORY = Category(
    id="visuals",
    name="Canvas & charts",
    icon="pie_chart",
    blurb="Custom drawing, charts and images.",
    demos=(
        Demo(id="signal", title="Custom canvas drawing",
             description="Rings, a smooth signal path and canvas text — "
                         "all drawn from Python.",
             build=lambda key: Column(
                 key=f"{key}_col", spacing=Spacing.MD,
                 children=[_signal(key),
                           Button("Reshuffle", key=f"{key}_shuffle",
                                  variant="tonal", icon=Icons.REFRESH
                                  ).on_click(_shuffle)]),
             tags=("canvas", "paint", "path", "draw")),
        Demo(id="sparkline", title="Sparkline",
             description="A one-call normalised line chart.",
             build=_sparkline, tags=("sparkline", "chart", "line")),
        Demo(id="charts", title="Charts",
             description="Line, bar, area and pie from the same series.",
             build=_charts, tags=("chart", "bar", "pie", "area")),
        Demo(id="images", title="Images",
             description="Network images, circle crops and placeholders.",
             build=_images, tags=("image", "network", "circle")),
    ),
)
