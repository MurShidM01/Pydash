"""Button demos — every variant, size and shape the SDK ships."""

from __future__ import annotations

from pydrud import (
    Button, ButtonBar, Colors, Column, Container, Divider, Elevation,
    FloatingActionButton, Icon, IconButton, Icons, Radius, ResponsiveGrid,
    Row, Spacing, Text, Theme, Tooltip, Widget,
)

from app.runtime import refresh
from app.state import State

__all__ = ["CATEGORY"]

#: Interactive counter proving the buttons really fire.
taps = State(0, name="button_taps")
pill = State(False, name="button_pill")
iconified = State(True, name="button_icons")


def _record(step: int = 1):
    def handler(_event):
        taps.value += step
        refresh()
    return handler


def _variants(key: str) -> Widget:
    note = ("Tapped {} time{}".format(taps.value,
                                      "" if taps.value == 1 else "s"))
    return Column(
        key=f"{key}_col",
        spacing=Spacing.MD,
        children=[
            ResponsiveGrid(
                key=f"{key}_grid",
                min_item_width=140,
                max_columns=2,
                spacing=Spacing.SM,
                children=[
                    Button("Filled", key=f"{key}_filled",
                           icon=Icons.CHECK if iconified.value else None
                           ).on_click(_record()),
                    Button("Tonal", key=f"{key}_tonal", variant="tonal",
                           icon=Icons.INFO if iconified.value else None
                           ).on_click(_record()),
                    Button("Outlined", key=f"{key}_outlined",
                           variant="outlined",
                           icon=Icons.STAR if iconified.value else None
                           ).on_click(_record()),
                    Button("Text", key=f"{key}_text", variant="text",
                           icon=Icons.SEND if iconified.value else None
                           ).on_click(_record()),
                    Button("Elevated", key=f"{key}_elevated",
                           variant="elevated",
                           icon=Icons.ROCKET if iconified.value else None
                           ).on_click(_record()),
                    Button("Disabled", key=f"{key}_disabled",
                           disabled=True),
                ],
            ),
            Divider(key=f"{key}_div"),
            Text(note, key=f"{key}_note", size=13, weight=600,
                 color=Theme.primary),
        ],
    )


def _sizes(key: str) -> Widget:
    return Row(
        key=f"{key}_row",
        spacing=Spacing.SM,
        vertical_alignment="center",
        children=[
            Button("Small", key=f"{key}_sm", size="sm",
                   pill=pill.value).on_click(_record()),
            Button("Medium", key=f"{key}_md", size="md",
                   pill=pill.value).on_click(_record()),
            Button("Large", key=f"{key}_lg", size="lg",
                   pill=pill.value).on_click(_record()),
        ],
    )


def _icon_buttons(key: str) -> Widget:
    return Row(
        key=f"{key}_row",
        spacing=Spacing.SM,
        children=[
            IconButton(Icons.FAVORITE, key=f"{key}_fav",
                       text="Favourite").on_click(_record()),
            IconButton(Icons.BOOKMARK, key=f"{key}_bookmark",
                       text="Bookmark").on_click(_record()),
            IconButton(Icons.SHARE, key=f"{key}_share",
                       text="Share").on_click(_record()),
            Tooltip("Long-press me", key=f"{key}_tip",
                    child=IconButton(Icons.HELP, key=f"{key}_help",
                                     text="Help").on_click(_record())),
        ],
    )


def _bar(key: str) -> Widget:
    return ButtonBar(
        key=f"{key}_bar",
        children=[
            Button("Cancel", key=f"{key}_cancel", variant="text"
                   ).on_click(lambda _e: None),
            Button("Save", key=f"{key}_save").on_click(_record(2)),
        ],
    )


def _fab(key: str) -> Widget:
    return Container(
        key=f"{key}_stage",
        width="match",
        height=150,
        border_radius=Radius.MD,
        bg=Theme.surface_variant,
        child=FloatingActionButton(
            "", key=f"{key}_fab", icon=Icons.ADD,
            bg_color=Theme.primary,
            bottom=18, right=18,
        ).on_click(_record(5)),
    )


def _toggle_pill(_event):
    pill.value = not pill.value
    refresh()


def _toggle_icons(_event):
    iconified.value = not iconified.value
    refresh()


def build_variants(key: str) -> Widget:
    return Column(
        key=f"{key}_body",
        spacing=Spacing.MD,
        children=[
            _variants(key),
            Divider(key=f"{key}_div2"),
            Button("Pill shape: on" if pill.value else "Pill shape: off",
                   key=f"{key}_pill_btn", variant="tonal",
                   on_click=_toggle_pill),
            _sizes(key),
        ],
    )


from app.data.catalog import Category, Demo  # noqa: E402

CATEGORY = Category(
    id="buttons",
    name="Buttons",
    icon="touch_app",
    blurb="Five Material variants, icon buttons, FABs and button bars.",
    demos=(
        Demo(id="variants", title="Variants & sizes",
             description="Filled, tonal, outlined, text and elevated — "
                         "small to large, square or pill.",
             build=build_variants,
             tags=("filled", "tonal", "outlined", "text", "elevated",
                   "pill")),
        Demo(id="icon", title="Icon buttons & tooltips",
             description="Compact icon actions with the native tooltip.",
             build=lambda key: Column(
                 key=f"{key}_body", spacing=Spacing.LG,
                 children=[_icon_buttons(key),
                           Divider(key=f"{key}_div"),
                           _bar(key)]),
             tags=("icon", "tooltip", "buttonbar")),
        Demo(id="fab", title="Floating action button",
             description="The FAB floats above its container with a real "
                         "shadow and ripple.",
             build=lambda key: _fab(key),
             tags=("fab", "float", "action")),
    ),
)
