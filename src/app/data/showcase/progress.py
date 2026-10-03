"""Progress, feedback and stepper demos."""

from __future__ import annotations

from pydrud import (
    Button, CircularProgress, Column, Container, Divider, Icon, Icons,
    ProgressBar, Radius, RefreshIndicator, Row, Spacing, Stepper, Text,
    Theme, Widget,
)

from app.runtime import current, refresh
from app.state import State

__all__ = ["CATEGORY"]

#: Interactive state.
download = State(0.25, name="progress_download")
ring = State(0.6, name="progress_ring")
step = State(1, name="progress_step")
refreshing = State(False, name="progress_refreshing")

STEPS = ("Account", "Profile", "Review", "Done")


def _bars(key: str) -> Widget:
    return Column(
        key=f"{key}_col",
        spacing=Spacing.LG,
        children=[
            Column(key=f"{key}_determinate", spacing=Spacing.XS, children=[
                Text(f"Downloading… {int(download.value * 100)}%",
                     key=f"{key}_dl_label", size=12,
                     color=Theme.text_secondary),
                ProgressBar(download.value, key=f"{key}_bar"),
            ]),
            Column(key=f"{key}_indeterminate", spacing=Spacing.XS, children=[
                Text("Indeterminate — working, unknown duration",
                     key=f"{key}_ind_label", size=12,
                     color=Theme.text_secondary),
                ProgressBar(key=f"{key}_bar_ind"),
            ]),
            Button("Boost progress", key=f"{key}_boost", variant="tonal",
                   icon=Icons.DOWNLOAD).on_click(_boost),
        ],
    )


def _boost(_event):
    download.value = min(1.0, download.value + 0.2)
    refresh()


def _rings(key: str) -> Widget:
    return Column(
        key=f"{key}_col",
        spacing=Spacing.LG,
        children=[
            Row(key=f"{key}_row", spacing=Spacing.XL,
                horizontal_alignment="center", children=[
                    CircularProgress(ring.value, key=f"{key}_ring",
                                     size=52, stroke=5),
                    CircularProgress(key=f"{key}_spin", size=52, stroke=5),
                ]),
            Button("Apply patch", key=f"{key}_apply", variant="tonal",
                   icon=Icons.SYNC).on_click(_patch_ring),
        ],
    )


def _patch_ring(_event):
    import random

    ring.value = round(random.uniform(0.1, 1.0), 2)
    refresh()


def _stepper(key: str) -> Widget:
    return Column(
        key=f"{key}_col",
        spacing=Spacing.MD,
        children=[
            Stepper(STEPS, key=f"{key}_stepper", current=step.value,
                    orientation="horizontal",
                    on_step=_set_step),
            Row(key=f"{key}_actions", spacing=Spacing.SM,
                horizontal_alignment="center", children=[
                    Button("Back", key=f"{key}_back", variant="outlined",
                           size="sm", disabled=step.value == 0
                           ).on_click(_move(-1)),
                    Button("Next", key=f"{key}_next", size="sm",
                           disabled=step.value == len(STEPS) - 1
                           ).on_click(_move(1)),
                ]),
        ],
    )


def _set_step(event):
    try:
        step.value = int(event.get("value", step.value))
    except (TypeError, ValueError):
        return
    refresh()


def _move(delta: int):
    def handler(_event):
        step.value = max(0, min(len(STEPS) - 1, step.value + delta))
        refresh()
    return handler


def _refresh(key: str) -> Widget:
    list_body = Column(
        key=f"{key}_content",
        spacing=Spacing.SM,
        children=[
            Text("Pull-to-refresh wraps any scrollable content. In this "
                 "demo the spinner resolves after a moment.",
                 key=f"{key}_hint", size=13,
                 color=Theme.text_secondary),
            Text("Refreshes: {}".format(_refresh_count.value),
                 key=f"{key}_count", size=13, weight=600,
                 color=Theme.primary),
        ],
    )
    return RefreshIndicator(
        key=f"{key}_indicator",
        refreshing=refreshing.value,
        on_refresh=_do_refresh,
        child=list_body,
    )


_refresh_count = State(0, name="progress_refresh_count")


def _do_refresh(_event):
    refreshing.value = True
    refresh()

    def finish():
        refreshing.value = False
        _refresh_count.value += 1
        app = current()
        if app is not None:
            app.page.end_refresh()
        refresh()

    from app.runtime import after

    after(1.2, finish)


from app.data.catalog import Category, Demo  # noqa: E402

CATEGORY = Category(
    id="progress",
    name="Progress & feedback",
    icon="sync",
    blurb="Linear and circular progress, steppers and pull-to-refresh.",
    demos=(
        Demo(id="bars", title="Linear progress",
             description="Determinate and indeterminate bars.",
             build=_bars, tags=("progressbar", "linear", "download")),
        Demo(id="rings", title="Circular progress",
             description="Spinner and value ring.",
             build=_rings, tags=("spinner", "ring", "circular")),
        Demo(id="stepper", title="Stepper",
             description="A wizard's step indicator with live state.",
             build=_stepper, tags=("stepper", "wizard", "steps")),
        Demo(id="refresh", title="Pull to refresh",
             description="Swipe the content down to trigger a refresh.",
             build=_refresh, tags=("refresh", "swipe", "pull")),
    ),
)
