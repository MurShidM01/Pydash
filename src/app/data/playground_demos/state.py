"""Reactive state — the counter that started it all, grown up."""

from __future__ import annotations

from pydrud import (
    Button, Card, CircularProgress, Colors, Column, Container, Divider,
    Icon, Icons, ProgressBar, Radius, ResponsiveGrid, Row, Spacing, StatCard,
    Text, Theme, Widget,
)

from app.runtime import current, refresh
from app.state import State

__all__ = ["DEMO"]

count = State(0, name="pg_count")
step_size = State(1, name="pg_step")
history = State((), name="pg_history")


def _change(step: int):
    def handler(_event):
        count.value += step
        history.value = (history.value + (count.value,))[-12:]
        page = _page()
        if page is not None:
            page.haptics.selection()
        refresh()
    return handler


def _reset(_event):
    previous = count.value
    count.value = 0
    history.value = ()

    def undo():
        count.value = previous
        refresh()

    page = _page()
    if page is not None:
        page.snack_bar("Counter reset", action="Undo", on_action=undo)
    refresh()


def _page():
    app = current()
    return app.page if app is not None else None


def build(key: str) -> Widget:
    value = count.value
    trend = _trend()
    return Column(
        key=f"{key}_col",
        spacing=Spacing.LG,
        children=[
            Card(
                key=f"{key}_hero",
                child=Column(
                    key=f"{key}_hero_col",
                    spacing=Spacing.XS,
                    horizontal_alignment="center",
                    children=[
                        Text("COUNTER", key=f"{key}_caption", size=11,
                             weight=700, color=Theme.text_secondary,
                             style={"font": {"letterSpacing": 0.14}}),
                        Text(str(value), key=f"{key}_value", size=56,
                             weight=800, color=Theme.primary),
                        Text(trend, key=f"{key}_trend", size=12,
                             color=Theme.text_secondary),
                    ],
                ),
                padding=Spacing.XL,
            ),
            ResponsiveGrid(
                key=f"{key}_actions",
                min_item_width=140,
                max_columns=3,
                spacing=Spacing.SM,
                children=[
                    Button("−1", key=f"{key}_dec", variant="tonal",
                           icon=Icons.REMOVE, size="md",
                           ).on_click(_change(-step_size.value)),
                    Button("+1", key=f"{key}_inc", icon=Icons.ADD,
                           size="md").on_click(_change(step_size.value)),
                    Button("Reset", key=f"{key}_reset", variant="outlined",
                           icon=Icons.REFRESH, size="md"
                           ).on_click(_reset),
                ],
            ),
            Card(
                key=f"{key}_steps",
                padding=Spacing.LG,
                child=Column(
                    key=f"{key}_steps_col",
                    spacing=Spacing.MD,
                    children=[
                        Text("Step size", key=f"{key}_step_label", size=13,
                             weight=600, color=Theme.text),
                        Row(key=f"{key}_step_row", spacing=Spacing.XS,
                            children=[
                                Button(str(n), key=f"{key}_step{n}",
                                       variant="filled"
                                       if step_size.value == n
                                       else "text", size="sm"
                                       ).on_click(_set_step(n))
                                for n in (1, 5, 10)
                            ]),
                        Divider(key=f"{key}_div"),
                        Row(
                            key=f"{key}_progress_row",
                            spacing=Spacing.MD,
                            vertical_alignment="center",
                            children=[
                                CircularProgress(
                                    min(1.0, abs(value) / 100),
                                    key=f"{key}_ring", size=34, stroke=4),
                                Column(
                                    key=f"{key}_progress_text",
                                    spacing=2,
                                    expand=1,
                                    children=[
                                        Text("Derived UI", key=f"{key}_derived",
                                             size=13, weight=600,
                                             color=Theme.text),
                                        Text("Every number above is a State "
                                             "read; handlers mutate it and "
                                             "call refresh().",
                                             key=f"{key}_derived_sub",
                                             size=12,
                                             color=Theme.text_secondary),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ),
            _spark_history(key),
        ],
    )


def _set_step(n: int):
    def handler(_event):
        step_size.value = n
        refresh()
    return handler


def _trend() -> str:
    if len(history.value) < 2:
        return "Make a move to start the history"
    delta = history.value[-1] - history.value[-2]
    if delta > 0:
        return f"↑ up {delta} from the last move"
    if delta < 0:
        return f"↓ down {abs(delta)} from the last move"
    return "flat"


def _spark_history(key: str) -> Widget:
    values = list(history.value) or [0]
    from pydrud import Canvas

    def draw(canvas: Canvas):
        canvas.sparkline(values, color=Theme.primary, width=2.5, fill=True)

    return Card(
        key=f"{key}_history",
        padding=Spacing.LG,
        child=Column(
            key=f"{key}_history_col",
            spacing=Spacing.SM,
            children=[
                Text("History", key=f"{key}_history_title", size=13,
                     weight=700, color=Theme.text),
                Canvas(key=f"{key}_history_canvas", width="match", height=72,
                       bg=Theme.surface_variant, on_draw=draw),
            ],
        ),
    )


from app.data.playground import PlaygroundDemo  # noqa: E402

DEMO = PlaygroundDemo(
    id="state",
    title="Reactive State",
    blurb="Counters, derived UI, undo and haptics — the state round-trip.",
    icon="swap",
    tags=("state", "counter", "refresh"),
    build=build,
)
