"""Live data — charts and canvas driven by a ticking state."""

from __future__ import annotations

import math
import random

from pydrud import (
    Button, Canvas, Chart, CircularProgress, Colors, Column, Icon, Icons,
    Radius, Row, Spacing, StatCard, Text, Theme, Widget,
)

from app.runtime import after, current, refresh
from app.state import State

__all__ = ["DEMO"]

series = State((18, 24, 20, 31, 27, 38, 33), name="pg_viz_series")
live = State(False, name="pg_viz_live")
frames = State(0, name="pg_viz_frames")


def _toggle_live(_event):
    live.value = not live.value
    refresh()
    if live.value:
        _schedule_tick()


def _schedule_tick():
    def tick():
        if not live.value:
            return
        _advance()
        _schedule_tick()
    after(1.0, tick)


def _advance(_event=None):
    values = list(series.value)[1:] + [random.randint(14, 44)]
    series.value = tuple(values)
    frames.value += 1
    refresh()


def build(key: str) -> Widget:
    values = list(series.value)
    latest = values[-1]
    average = sum(values) / len(values)
    return Column(
        key=f"{key}_col",
        spacing=Spacing.LG,
        children=[
            Row(
                key=f"{key}_stats",
                spacing=Spacing.SM,
                children=[
                    StatCard("Latest", latest, key=f"{key}_stat_latest",
                             icon=Icons.TRENDING_UP),
                    StatCard("Average", f"{average:.1f}",
                             key=f"{key}_stat_avg", icon=Icons.CHART),
                ],
            ),
            Chart(
                values,
                key=f"{key}_chart",
                kind="area",
                labels=["6d", "5d", "4d", "3d", "2d", "yday", "now"],
                height=180,
                show_grid=True,
            ),
            _dial(key),
            Row(
                key=f"{key}_actions",
                spacing=Spacing.SM,
                horizontal_alignment="center",
                children=[
                    Button("Advance", key=f"{key}_advance", variant="tonal",
                           icon=Icons.SKIP_NEXT).on_click(_advance),
                    Button("Live" if not live.value else "Pause",
                           key=f"{key}_live", icon=
                           Icons.PAUSE if live.value else Icons.PLAY
                           ).on_click(_toggle_live),
                ],
            ),
            Text(f"{frames.value} frames rendered", key=f"{key}_frames",
                 size=12, color=Theme.text_secondary, text_align="center"),
        ],
    )


def _dial(key: str) -> Widget:
    ratio = min(1.0, list(series.value)[-1] / 44)

    def draw(canvas: Canvas):
        canvas.arc(0.5, 0.5, 0.42, start=135, sweep=270, pie=False,
                   color=Colors.with_opacity(Theme.primary, 0.15), width=14)
        canvas.arc(0.5, 0.5, 0.42, start=135, sweep=270 * ratio, pie=False,
                   color=Theme.primary, width=14)
        canvas.text(f"{int(ratio * 100)}%", 0.5, 0.55, size=22, weight=800,
                    color=Theme.text, align="center")
        canvas.text("load", 0.5, 0.72, size=10,
                    color=Theme.text_secondary, align="center")

    return Canvas(
        key=f"{key}_dial",
        width="match",
        height=170,
        bg=Theme.surface_variant,
        on_draw=draw,
    )


from app.data.playground import PlaygroundDemo  # noqa: E402

DEMO = PlaygroundDemo(
    id="viz",
    title="Live Data",
    blurb="Charts and canvas gauges updating from a ticking state.",
    icon="trending_up",
    tags=("chart", "canvas", "live"),
    build=build,
)
