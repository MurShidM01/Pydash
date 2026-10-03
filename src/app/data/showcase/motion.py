"""Motion & gesture demos — animation wrappers, gestures, drag and dismiss."""

from __future__ import annotations

from pydrud import (
    AnimatedContainer, AnimatedOpacity, AnimatedScale, AnimatedSwitcher,
    Animation, Button, Colors, Column, Container, Dismissible, Divider,
    Draggable, GestureDetector, Icon, Icons, Radius, Row, Spacing, Text,
    Theme, Widget,
)

from app.runtime import refresh
from app.state import State
from app.theme import pad

__all__ = ["CATEGORY"]

#: Interactive state.
morph_big = State(True, name="motion_morph")
opacity_on = State(True, name="motion_opacity")
scale_on = State(True, name="motion_scale")
switcher_a = State(True, name="motion_switcher")
swipe_note = State("Swipe me", name="motion_swipe")
drag_offset = State(0.5, name="motion_drag")
tasks = State(("Sketch the UI", "Wire the state", "Polish the motion",
               "Ship it"), name="motion_tasks")


def _morph(key: str) -> Widget:
    big = morph_big.value
    return Column(
        key=f"{key}_col",
        spacing=Spacing.MD,
        horizontal_alignment="center",
        children=[
            AnimatedContainer(
                key=f"{key}_box",
                width=220 if big else 120,
                height=120 if big else 220,
                bg=Theme.primary if big else Theme.secondary,
                border_radius=Radius.PILL if not big else Radius.LG,
                animation=Animation.springy(),
                child=Icon(Icons.SPARKLE if big else Icons.PALETTE,
                           key=f"{key}_icon", size=30, color=Colors.WHITE),
            ),
            Button("Morph", key=f"{key}_toggle", variant="tonal",
                   icon=Icons.SWAP).on_click(_flip_morph),
        ],
    )


def _flip_morph(_event):
    morph_big.value = not morph_big.value
    refresh()


def _opacity_scale(key: str) -> Widget:
    return Column(
        key=f"{key}_col",
        spacing=Spacing.LG,
        children=[
            Row(key=f"{key}_row", spacing=Spacing.LG,
                horizontal_alignment="center", children=[
                    AnimatedOpacity(
                        key=f"{key}_fade",
                        opacity=1.0 if opacity_on.value else 0.15,
                        animation=Animation(400),
                        child=Container(
                            key=f"{key}_fade_tile", width=80, height=80,
                            border_radius=Radius.MD, bg=Theme.primary,
                            alignment="center",
                            child=Icon(Icons.VISIBILITY,
                                       key=f"{key}_fade_icon", size=26,
                                       color=Colors.WHITE),
                        ),
                    ),
                    AnimatedScale(
                        key=f"{key}_zoom",
                        scale=1.0 if scale_on.value else 0.6,
                        animation=Animation(320, curve="overshoot"),
                        child=Container(
                            key=f"{key}_zoom_tile", width=80, height=80,
                            border_radius=Radius.MD, bg=Theme.secondary,
                            alignment="center",
                            child=Icon(Icons.ZOOM_IN,
                                       key=f"{key}_zoom_icon", size=26,
                                       color=Colors.WHITE),
                        ),
                    ),
                ]),
            Row(key=f"{key}_btns", spacing=Spacing.SM,
                horizontal_alignment="center", children=[
                    Button("Fade", key=f"{key}_fade_btn", variant="tonal",
                           size="sm").on_click(_flip_opacity),
                    Button("Scale", key=f"{key}_scale_btn", variant="tonal",
                           size="sm").on_click(_flip_scale),
                ]),
        ],
    )


def _flip_opacity(_event):
    opacity_on.value = not opacity_on.value
    refresh()


def _flip_scale(_event):
    scale_on.value = not scale_on.value
    refresh()


def _switcher(key: str) -> Widget:
    first = switcher_a.value
    current = Container(
        key=f"{key}_a" if first else f"{key}_b",
        width="match",
        padding=Spacing.LG,
        border_radius=Radius.LG,
        bg=Theme.primary if first else Theme.secondary,
        child=Column(
            key=f"{key}_a_col" if first else f"{key}_b_col",
            spacing=2,
            children=[
                Text("Panel A" if first else "Panel B",
                     key=f"{key}_title", size=16, weight=700,
                     color=Colors.WHITE),
                Text("AnimatedSwitcher cross-fades between its children "
                     "when the key changes.",
                     key=f"{key}_sub", size=12,
                     color=Colors.with_opacity(Colors.WHITE, 0.85)),
            ],
        ),
    )
    return Column(
        key=f"{key}_col",
        spacing=Spacing.MD,
        children=[
            AnimatedSwitcher(key=f"{key}_switcher", child=current,
                             animation=Animation(280)),
            Button("Swap", key=f"{key}_swap", variant="tonal",
                   icon=Icons.SWAP).on_click(_flip_switcher),
        ],
    )


def _flip_switcher(_event):
    switcher_a.value = not switcher_a.value
    refresh()


def _gestures(key: str) -> Widget:
    return Column(
        key=f"{key}_col",
        spacing=Spacing.MD,
        children=[
            GestureDetector(
                key=f"{key}_pad",
                child=Container(
                    key=f"{key}_pad_box",
                    width="match",
                    height=110,
                    border_radius=Radius.LG,
                    bg=Theme.surface_variant,
                    alignment="center",
                    child=Text(swipe_note.value, key=f"{key}_pad_text",
                               size=15, weight=600, color=Theme.text),
                ),
                on_swipe_left=lambda e: _swipe("Swiped left ←"),
                on_swipe_right=lambda e: _swipe("Swiped right →"),
                on_swipe_up=lambda e: _swipe("Swiped up ↑"),
                on_swipe_down=lambda e: _swipe("Swiped down ↓"),
                on_double_tap=lambda e: _swipe("Double tap!"),
            ),
            Text("Gestures: swipe in any direction or double-tap.",
                 key=f"{key}_hint", size=12,
                 color=Theme.text_secondary, text_align="center"),
        ],
    )


def _swipe(note: str):
    swipe_note.value = note
    refresh()


def _dismissible(key: str) -> Widget:
    rows = []
    for index, task in enumerate(tasks.value):
        rows.append(Dismissible(
            key=f"{key}_item{index}",
            child=Container(
                key=f"{key}_tile{index}",
                width="match",
                padding=pad(horizontal=Spacing.MD, vertical=Spacing.SM + 2),
                bg=Theme.surface,
                border_radius=Radius.SM,
                style={"border": {"color": Theme.outline, "width": 1}},
                child=Row(
                    key=f"{key}_row{index}",
                    spacing=Spacing.SM,
                    vertical_alignment="center",
                    children=[
                        Icon(Icons.DRAG, key=f"{key}_icon{index}", size=16,
                             color=Theme.text_secondary),
                        Text(task, key=f"{key}_text{index}", size=14,
                             color=Theme.text),
                    ],
                ),
            ),
            direction="end",
            background=Colors.ERROR,
            icon=Icons.DELETE,
            on_dismiss=lambda e, i=index: _dismiss(i),
        ))
    if not rows:
        return Column(key=f"{key}_empty_col", spacing=Spacing.SM,
                      children=[
                          Text("All dismissed.", key=f"{key}_allgone",
                               size=14, color=Theme.text_secondary),
                          Button("Restore", key=f"{key}_restore",
                                 variant="tonal",
                                 icon=Icons.UNDO).on_click(_restore),
                      ])
    return Column(key=f"{key}_col", spacing=Spacing.SM, children=rows)


def _dismiss(index: int):
    remaining = tuple(t for i, t in enumerate(tasks.value) if i != index)
    tasks.value = remaining
    refresh()


def _restore(_event):
    tasks.value = ("Sketch the UI", "Wire the state", "Polish the motion",
                   "Ship it")
    refresh()


def _draggable(key: str) -> Widget:
    from pydrud import Slider

    return Column(
        key=f"{key}_col",
        spacing=Spacing.MD,
        children=[
            Draggable(
                key=f"{key}_dragger",
                axis="horizontal",
                child=Container(
                    key=f"{key}_knob",
                    width=56,
                    height=56,
                    border_radius=Radius.PILL,
                    bg=Theme.primary,
                    alignment="center",
                    child=Icon(Icons.DRAG, key=f"{key}_knob_icon", size=22,
                               color=Colors.WHITE),
                ),
                on_drag=lambda e: _dragged(e),
            ),
            Text("Offset: {:.0f} dp".format(drag_offset.value * 240),
                 key=f"{key}_label", size=13, weight=600,
                 color=Theme.primary),
            Slider(drag_offset.value, key=f"{key}_slider", min=0.0, max=1.0
                   ).on_change(_set_drag),
        ],
    )


def _dragged(event):
    data = event.data if hasattr(event, "data") else {}
    dx = float(data.get("dx", 0) or 0)
    drag_offset.value = max(0.0, min(1.0, drag_offset.value + dx / 240))
    refresh()


def _set_drag(event):
    try:
        drag_offset.value = float(event.get("value", drag_offset.value))
    except (TypeError, ValueError):
        return
    refresh()


from app.data.catalog import Category, Demo  # noqa: E402

CATEGORY = Category(
    id="motion",
    name="Motion & gestures",
    icon="animation",
    blurb="Implicit animations, entrance effects, gestures, drag and dismiss.",
    demos=(
        Demo(id="morph", title="Animated containers",
             description="Size, colour and corner radius tween on change.",
             build=_morph, tags=("animated", "spring", "morph")),
        Demo(id="fade", title="Opacity & scale",
             description="AnimatedOpacity and AnimatedScale wrappers.",
             build=_opacity_scale, tags=("fade", "scale", "opacity")),
        Demo(id="switcher", title="AnimatedSwitcher",
             description="Cross-fades between two panels.",
             build=_switcher, tags=("switcher", "crossfade")),
        Demo(id="gestures", title="Gesture pad",
             description="Swipes and double-taps reported live.",
             build=_gestures, tags=("gesture", "swipe", "tap")),
        Demo(id="dismissible", title="Dismissible rows",
             description="Swipe a row away; restore when they're gone.",
             build=_dismissible, tags=("dismiss", "swipe", "list")),
        Demo(id="draggable", title="Draggable",
             description="A draggable knob reporting its offset.",
             build=_draggable, tags=("drag", "drop", "axis")),
    ),
)
