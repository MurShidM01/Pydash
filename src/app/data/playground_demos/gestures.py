"""Gesture gallery — taps, swipes, double-taps and pan, reported live."""

from __future__ import annotations

from pydrud import (
    Card, Colors, Column, Container, Divider, Icon, Icons, Radius, Row,
    Spacing, Text, Theme, Widget,
)
from pydrud import GestureDetector, InkWell

from app.runtime import refresh
from app.state import State

__all__ = ["DEMO"]

last_gesture = State("Touch the pads", name="pg_gesture_last")
taps = State(0, name="pg_gesture_taps")


def _report(name: str, detail: str = ""):
    def handler(event):
        data = getattr(event, "data", None) or {}
        extra = detail
        if not extra and data:
            extra = ", ".join(f"{k} {round(v, 1) if isinstance(v, float) else v}"
                              for k, v in data.items()
                              if k in ("dx", "dy", "velocity", "scale", "x",
                                       "y"))
        last_gesture.value = f"{name}{(' · ' + extra) if extra else ''}"
        if name == "Tap" or name == "Double tap":
            taps.value += 1
        refresh()
    return handler


def build(key: str) -> Widget:
    return Column(
        key=f"{key}_col",
        spacing=Spacing.LG,
        children=[
            Card(
                key=f"{key}_readout",
                padding=Spacing.LG,
                child=Row(
                    key=f"{key}_readout_row",
                    spacing=Spacing.MD,
                    vertical_alignment="center",
                    children=[
                        Icon(Icons.FINGERPRINT, key=f"{key}_readout_icon",
                             size=26, color=Theme.primary),
                        Column(
                            key=f"{key}_readout_col",
                            spacing=2,
                            expand=1,
                            children=[
                                Text(last_gesture.value,
                                     key=f"{key}_readout_text", size=14,
                                     weight=600, color=Theme.text),
                                Text(f"{taps.value} taps registered",
                                     key=f"{key}_readout_taps", size=12,
                                     color=Theme.text_secondary),
                            ],
                        ),
                    ],
                ),
            ),
            GestureDetector(
                key=f"{key}_pad",
                child=Container(
                    key=f"{key}_pad_box",
                    width="match",
                    height=170,
                    border_radius=Radius.LG,
                    bg=Colors.with_opacity(Theme.primary, 0.10),
                    alignment="center",
                    child=Column(
                        key=f"{key}_pad_col",
                        spacing=Spacing.XS,
                        horizontal_alignment="center",
                        children=[
                            Icon(Icons.TOUCH_APP if hasattr(Icons, "TOUCH_APP")
                                 else Icons.SPARKLE,
                                 key=f"{key}_pad_icon", size=32,
                                 color=Theme.primary),
                            Text("Swipe, double-tap or drag here",
                                 key=f"{key}_pad_text", size=13,
                                 weight=600, color=Theme.text),
                        ],
                    ),
                ),
                on_tap=_report("Tap"),
                on_double_tap=_report("Double tap"),
                on_long_press=_report("Long press"),
                on_swipe_left=_report("Swipe left"),
                on_swipe_right=_report("Swipe right"),
                on_swipe_up=_report("Swipe up"),
                on_swipe_down=_report("Swipe down"),
                on_pan_update=_report("Pan"),
                on_scale=_report("Scale"),
            ),
            Row(
                key=f"{key}_inks",
                spacing=Spacing.SM,
                children=[
                    _ink(key, "ripple_a", "Ripple A", Icons.SPARKLE),
                    _ink(key, "ripple_b", "Ripple B", Icons.STAR),
                ],
            ),
            Text("GestureDetector exposes tap, double-tap, long-press, "
                 "swipes, pan and pinch; InkWell adds the Material ripple "
                 "to any child.",
                 key=f"{key}_note", size=12,
                 color=Theme.text_secondary, text_align="center"),
        ],
    )


def _ink(key: str, name: str, label: str, icon: str) -> Widget:
    return Container(
        key=f"{key}_{name}_wrap",
        expand=1,
        border_radius=Radius.MD,
        style={"border": {"color": Theme.outline, "width": 1}},
        child=InkWell(
            key=f"{key}_{name}",
            child=Container(
                key=f"{key}_{name}_box",
                width="match",
                padding=Spacing.LG,
                alignment="center",
                child=Row(
                    key=f"{key}_{name}_row",
                    spacing=Spacing.SM,
                    horizontal_alignment="center",
                    vertical_alignment="center",
                    children=[
                        Icon(icon, key=f"{key}_{name}_icon", size=16,
                             color=Theme.primary),
                        Text(label, key=f"{key}_{name}_label", size=13,
                             weight=600, color=Theme.text),
                    ],
                ),
            ),
            radius=14,
            on_click=_report(label + " tap"),
        ),
    )


from app.data.playground import PlaygroundDemo  # noqa: E402

DEMO = PlaygroundDemo(
    id="gestures",
    title="Gesture Gallery",
    blurb="Every gesture the framework detects, reported live.",
    icon="drag",
    tags=("gesture", "swipe", "ripple"),
    build=build,
)
