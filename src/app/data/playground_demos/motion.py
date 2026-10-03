"""Motion lab — orchestrate the animation widgets into one machine."""

from __future__ import annotations

import math

from pydrud import (
    AnimatedContainer, AnimatedOpacity, AnimatedRotation, AnimatedSwitcher,
    Animation, Button, Canvas, Card, Colors, Column, Container, Icon,
    Icons, Radius, Row, Spacing, Text, Theme, Widget,
)

from app.runtime import refresh
from app.state import State

__all__ = ["DEMO"]

on = State(True, name="pg_motion_on")
spins = State(0, name="pg_motion_spins")


def _toggle(_event):
    on.value = not on.value
    refresh()


def _spin(_event):
    spins.value += 45
    refresh()


def build(key: str) -> Widget:
    active = on.value
    return Column(
        key=f"{key}_col",
        spacing=Spacing.LG,
        children=[
            Card(
                key=f"{key}_stage_card",
                padding=Spacing.LG,
                child=Column(
                    key=f"{key}_stage_col",
                    spacing=Spacing.LG,
                    children=[
                        Container(
                            key=f"{key}_stage",
                            width="match",
                            height=200,
                            border_radius=Radius.LG,
                            bg=Theme.surface_variant,
                            alignment="center",
                            child=Row(
                                key=f"{key}_row",
                                spacing=Spacing.LG,
                                horizontal_alignment="center",
                                vertical_alignment="center",
                                children=[
                                    AnimatedRotation(
                                        degrees=spins.value,
                                        key=f"{key}_rot",
                                        animation=Animation(
                                            600, curve="decelerate"),
                                        child=Container(
                                            key=f"{key}_rot_tile",
                                            width=64, height=64,
                                            border_radius=Radius.MD,
                                            bg=Theme.primary,
                                            alignment="center",
                                            child=Icon(
                                                Icons.REFRESH,
                                                key=f"{key}_rot_icon",
                                                size=26,
                                                color=Colors.WHITE),
                                        ),
                                    ),
                                    AnimatedContainer(
                                        key=f"{key}_pulse",
                                        width=96 if active else 48,
                                        height=96 if active else 48,
                                        bg=Theme.secondary if active
                                        else Theme.outline,
                                        border_radius=Radius.PILL,
                                        animation=Animation.springy(),
                                    ),
                                    AnimatedOpacity(
                                        opacity=1.0 if active else 0.15,
                                        key=f"{key}_fade",
                                        animation=Animation(450),
                                        child=Icon(
                                            Icons.SPARKLE,
                                            key=f"{key}_fade_icon", size=34,
                                            color=Theme.primary),
                                    ),
                                ],
                            ),
                        ),
                        Row(
                            key=f"{key}_actions",
                            spacing=Spacing.SM,
                            horizontal_alignment="center",
                            children=[
                                Button("Pulse", key=f"{key}_pulse_btn",
                                       variant="tonal", icon=Icons.SWAP
                                       ).on_click(_toggle),
                                Button("Rotate 45°", key=f"{key}_rot_btn",
                                       variant="tonal",
                                       icon=Icons.REFRESH).on_click(_spin),
                            ],
                        ),
                    ],
                ),
            ),
            _switcher_card(key),
        ],
    )


def _switcher_card(key: str) -> Widget:
    phase = "idle" if not on.value else "live"
    panel = Container(
        key=f"{key}_panel_{phase}",
        width="match",
        padding=Spacing.LG,
        border_radius=Radius.LG,
        bg=Theme.primary if phase == "live" else Theme.surface,
        style=({"border": {"color": Theme.outline, "width": 1}}
               if phase == "idle" else {}),
        child=Row(
            key=f"{key}_panel_{phase}_row",
            spacing=Spacing.MD,
            vertical_alignment="center",
            children=[
                Icon(Icons.TERMINAL if phase == "live" else Icons.PAUSE,
                     key=f"{key}_panel_{phase}_icon", size=20,
                     color=Colors.WHITE if phase == "live"
                     else Theme.text_secondary),
                Column(
                    key=f"{key}_panel_{phase}_col",
                    spacing=2,
                    expand=1,
                    children=[
                        Text("Render loop: " + phase,
                             key=f"{key}_panel_{phase}_title", size=14,
                             weight=700,
                             color=Colors.WHITE if phase == "live"
                             else Theme.text),
                        Text("AnimatedSwitcher cross-fades whole panels "
                             "when their key changes.",
                             key=f"{key}_panel_{phase}_sub", size=12,
                             color=Colors.with_opacity(Colors.WHITE, 0.85)
                             if phase == "live"
                             else Theme.text_secondary),
                    ],
                ),
            ],
        ),
    )
    return Card(
        key=f"{key}_switcher_card",
        padding=Spacing.LG,
        child=Column(
            key=f"{key}_switcher_col",
            spacing=Spacing.MD,
            children=[
                AnimatedSwitcher(key=f"{key}_switcher", child=panel,
                                 animation=Animation(300)),
            ],
        ),
    )


from app.data.playground import PlaygroundDemo  # noqa: E402

DEMO = PlaygroundDemo(
    id="motion",
    title="Motion Lab",
    blurb="Rotation, pulse, fade and switcher choreography.",
    icon="sparkle",
    tags=("animation", "rotate", "fade"),
    build=build,
)
