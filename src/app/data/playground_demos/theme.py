"""Theme studio — re-seed the whole design system live."""

from __future__ import annotations

from pydrud import (
    Button, Card, Colors, Column, Container, Divider, Icon, Icons, Radius,
    Row, Spacing, Switch, Text, Theme, Widget,
)

from app.runtime import current, refresh
from app.state import State, theme_mode

__all__ = ["DEMO"]

seed = State("#FF6366F1", name="pg_seed")

SEEDS = (
    ("Indigo", "#FF6366F1"),
    ("Teal", "#FF14B8A6"),
    ("Rose", "#FFF43F5E"),
    ("Amber", "#FFF59E0B"),
    ("Emerald", "#FF22C55E"),
    ("Slate", "#FF64748B"),
)


def _reseed(color: str):
    def handler(_event):
        seed.value = color
        app = current()
        page = app.page if app is not None else None
        if page is not None:
            page.set_theme(color, dark=Theme.dark_mode or None)
        refresh()
    return handler


def _set_mode(mode: str):
    def handler(_event):
        theme_mode.value = mode
        app = current()
        page = app.page if app is not None else None
        if page is not None:
            page.set_theme_mode(mode)
        refresh()
    return handler


def build(key: str) -> Widget:
    current_mode = theme_mode.value if theme_mode.value != "system" else (
        "dark" if Theme.dark_mode else "light")
    return Column(
        key=f"{key}_col",
        spacing=Spacing.LG,
        children=[
            Card(
                key=f"{key}_swatch",
                padding=Spacing.LG,
                child=Column(
                    key=f"{key}_swatch_col",
                    spacing=Spacing.MD,
                    children=[
                        Text("Brand seed", key=f"{key}_seed_title", size=13,
                             weight=700, color=Theme.text),
                        Row(
                            key=f"{key}_seeds",
                            spacing=Spacing.SM,
                            children=[
                                Container(
                                    key=f"{key}_seed_{name.lower()}",
                                    width=44,
                                    height=44,
                                    border_radius=Radius.PILL,
                                    bg=color,
                                    alignment="center",
                                    on_click=_reseed(color),
                                    child=(Icon(Icons.CHECK,
                                                key=f"{key}_check_{name.lower()}",
                                                size=18,
                                                color=Colors.WHITE)
                                           if seed.value == color
                                           else Container(
                                               key=f"{key}_nocheck_{name.lower()}",
                                               width=0, height=0)),
                                )
                                for name, color in SEEDS
                            ],
                        ),
                        Text("One call — Theme.seed + apply_theme — "
                             "re-derives the palette, tokens and native "
                             "widgets together.",
                             key=f"{key}_seed_note", size=12,
                             color=Theme.text_secondary),
                    ],
                ),
            ),
            Card(
                key=f"{key}_mode",
                padding=Spacing.LG,
                child=Column(
                    key=f"{key}_mode_col",
                    spacing=Spacing.MD,
                    children=[
                        Text("Appearance", key=f"{key}_mode_title", size=13,
                             weight=700, color=Theme.text),
                        Row(key=f"{key}_mode_row", spacing=Spacing.XS,
                            children=[
                                Button("Light", key=f"{key}_light",
                                       variant="filled"
                                       if current_mode == "light"
                                       else "outlined", size="sm",
                                       icon=Icons.LIGHT_MODE
                                       ).on_click(_set_mode("light")),
                                Button("Dark", key=f"{key}_dark",
                                       variant="filled"
                                       if current_mode == "dark"
                                       else "outlined", size="sm",
                                       icon=Icons.DARK_MODE
                                       ).on_click(_set_mode("dark")),
                                Button("System", key=f"{key}_system",
                                       variant="filled"
                                       if theme_mode.value == "system"
                                       else "outlined", size="sm"
                                       ).on_click(_set_mode("system")),
                            ]),
                    ],
                ),
            ),
            Card(
                key=f"{key}_roles",
                padding=Spacing.LG,
                child=Column(
                    key=f"{key}_roles_col",
                    spacing=Spacing.MD,
                    children=[
                        Text("Generated roles", key=f"{key}_roles_title",
                             size=13, weight=700, color=Theme.text),
                        Row(key=f"{key}_roles_row", spacing=Spacing.XS,
                            children=[
                                _role(key, "primary", Theme.primary),
                                _role(key, "secondary", Theme.secondary),
                                _role(key, "surface", Theme.surface),
                                _role(key, "variant", Theme.surface_variant),
                                _role(key, "error", Theme.error),
                            ]),
                        Divider(key=f"{key}_div"),
                        Row(
                            key=f"{key}_buttons",
                            spacing=Spacing.XS,
                            children=[
                                Button("Filled", key=f"{key}_b1"),
                                Button("Tonal", key=f"{key}_b2",
                                       variant="tonal"),
                                Button("Text", key=f"{key}_b3",
                                       variant="text"),
                            ],
                        ),
                        Switch("A native switch reading the same palette",
                               key=f"{key}_switch", active=True),
                    ],
                ),
            ),
        ],
    )


def _role(key: str, name: str, color: str) -> Widget:
    return Container(
        key=f"{key}_role_{name}",
        width=44,
        height=44,
        border_radius=Radius.MD,
        bg=color,
        alignment="center",
        child=Text(name[0].upper(), key=f"{key}_role_{name}_t", size=13,
                   weight=700, color=Colors.on(color)),
    )


from app.data.playground import PlaygroundDemo  # noqa: E402

DEMO = PlaygroundDemo(
    id="theme",
    title="Theme Studio",
    blurb="Re-seed the palette and flip light/dark — live, everywhere.",
    icon="palette",
    tags=("theme", "color", "dark"),
    build=build,
)
