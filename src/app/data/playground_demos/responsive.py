"""Responsive lab — watch layouts adapt to the live window metrics."""

from __future__ import annotations

from pydrud import (
    AdaptiveLayout, Card, Colors, Column, Container, Icon, Icons, Radius,
    Responsive, ResponsiveBuilder, Row, ShowWhen, Spacing, Text, Theme,
    Widget,
)
from pydrud.core.responsive import MediaQuery

from app.runtime import refresh
from app.state import State

__all__ = ["DEMO"]

density_note = State("", name="pg_resp_note")


def build(key: str) -> Widget:
    info = MediaQuery.info()
    breakpoint = str(info.breakpoint)

    cards = [
        _metric(key, 0, "Window", f"{info.width:.0f}×{info.height:.0f} dp",
                Icons.DASHBOARD),
        _metric(key, 1, "Class", breakpoint.capitalize(), Icons.LAYERS),
        _metric(key, 2, "Orientation", str(info.orientation).capitalize(),
                Icons.SWAP),
        _metric(key, 3, "Density",
                f"{getattr(info, 'density', 2.0):.2f}×", Icons.GRID),
    ]

    def compact():
        return Column(key=f"{key}_compact",
                      spacing=Spacing.SM,
                      children=[_pane(key, "compact", "One column",
                                      "Phones: everything stacks.")])

    def medium():
        return Row(key=f"{key}_medium", spacing=Spacing.SM, children=[
            _pane(key, "medium_a", "Two up",
                  "Small tablets and landscape."),
            _pane(key, "medium_b", "Rail appears",
                  "Navigation moves to the side."),
        ])

    def expanded():
        return Row(key=f"{key}_expanded", spacing=Spacing.SM, children=[
            _pane(key, "expanded_a", "Three up", "Tablets and desktops."),
            _pane(key, "expanded_b", "Content capped",
                  "Lines stay readable."),
            _pane(key, "expanded_c", "Max width", "Whitespace wins."),
        ])

    return Column(
        key=f"{key}_col",
        spacing=Spacing.LG,
        children=[
            AdaptiveLayout(
                key=f"{key}_adaptive",
                compact=compact(),
                medium=medium(),
                expanded=expanded(),
            ),
            Card(
                key=f"{key}_metrics_card",
                padding=Spacing.LG,
                child=Column(
                    key=f"{key}_metrics_col",
                    spacing=Spacing.MD,
                    children=[
                        Text("Live metrics", key=f"{key}_metrics_title",
                             size=13, weight=700, color=Theme.text),
                        Column(
                            key=f"{key}_metrics_list",
                            spacing=Spacing.SM,
                            children=cards,
                        ),
                        Text("Rotate the device, split the screen or "
                             "change the font size — the app receives a "
                             "metrics event, rebuilds and reflows.",
                             key=f"{key}_metrics_note", size=12,
                             color=Theme.text_secondary),
                    ],
                ),
            ),
            ShowWhen(
                Container(
                    key=f"{key}_wide",
                    width="match",
                    padding=Spacing.MD,
                    border_radius=Radius.MD,
                    bg=Colors.with_opacity(Theme.primary, 0.12),
                    child=Text("≥ 600dp: you are seeing the wide layout "
                               "right now.", key=f"{key}_wide_text",
                               size=13, color=Theme.text),
                ),
                min_width=600,
                key=f"{key}_show_wide",
            ),
        ],
    )


def _pane(key: str, name: str, title: str, note: str) -> Widget:
    return Container(
        key=f"{key}_pane_{name}",
        expand=1,
        padding=Spacing.MD,
        border_radius=Radius.MD,
        bg=Theme.surface_variant,
        child=Column(
            key=f"{key}_pane_{name}_col",
            spacing=2,
            children=[
                Text(title, key=f"{key}_pane_{name}_t", size=13,
                     weight=700, color=Theme.text),
                Text(note, key=f"{key}_pane_{name}_n", size=11,
                     color=Theme.text_secondary),
            ],
        ),
    )


def _metric(key: str, index: int, label: str, value: str,
            icon: str) -> Widget:
    return Row(
        key=f"{key}_metric{index}",
        spacing=Spacing.SM,
        vertical_alignment="center",
        children=[
            Icon(icon, key=f"{key}_metric{index}_icon", size=16,
                 color=Theme.primary),
            Text(label, key=f"{key}_metric{index}_label", size=13,
                 color=Theme.text_secondary, expand=1),
            Text(value, key=f"{key}_metric{index}_value", size=13,
                 weight=600, color=Theme.text),
        ],
    )


from app.data.playground import PlaygroundDemo  # noqa: E402

DEMO = PlaygroundDemo(
    id="responsive",
    title="Responsive Lab",
    blurb="Adaptive layouts that follow the live window metrics.",
    icon="dashboard",
    tags=("responsive", "adaptive", "breakpoint"),
    build=build,
)
