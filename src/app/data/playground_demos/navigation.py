"""Navigation — stack pushes, parameters, transitions and back handling."""

from __future__ import annotations

from pydrud import (
    AppBar, Badge, Button, Card, Column, Container, Divider, EdgeInsets,
    Icon, Icons, ListTile, Radius, Row, Spacing, Text, Theme, Widget,
)

from app.runtime import current, refresh, router
from app.state import State

__all__ = ["DEMO", "item_screen"]

visits = State(0, name="pg_nav_visits")


def _open(index: int, transition: str):
    def handler(_event):
        visits.value += 1
        router.push("playground/item", index=index, via=transition)
        refresh()
    return handler


def build(key: str) -> Widget:
    return Column(
        key=f"{key}_col",
        spacing=Spacing.LG,
        children=[
            Card(
                key=f"{key}_card",
                padding=Spacing.LG,
                child=Column(
                    key=f"{key}_card_col",
                    spacing=Spacing.MD,
                    children=[
                        Text("Push a screen onto the stack",
                             key=f"{key}_title", size=15, weight=700,
                             color=Theme.text),
                        Text("Each row pushes with a different transition. "
                             "Use the back gesture, the app bar arrow or "
                             "the button on the next screen to pop.",
                             key=f"{key}_sub", size=13,
                             color=Theme.text_secondary),
                        Divider(key=f"{key}_div"),
                        ListTile("Slide in from the right",
                                 key=f"{key}_slide", leading=Icons.FORWARD,
                                 trailing=Icons.CHEVRON_RIGHT,
                                 on_click=_open(1, "slide_left")),
                        Divider(key=f"{key}_div2"),
                        ListTile("Fade through",
                                 key=f"{key}_fade", leading=Icons.EXPAND_MORE,
                                 trailing=Icons.CHEVRON_RIGHT,
                                 on_click=_open(2, "fade")),
                        Divider(key=f"{key}_div3"),
                        ListTile("Scale up", key=f"{key}_scale",
                                 leading=Icons.ZOOM_IN,
                                 trailing=Icons.CHEVRON_RIGHT,
                                 on_click=_open(3, "scale")),
                    ],
                ),
            ),
            Card(
                key=f"{key}_stats",
                padding=Spacing.LG,
                child=Column(
                    key=f"{key}_stats_col",
                    spacing=Spacing.SM,
                    children=[
                        Row(
                            key=f"{key}_stats_row",
                            spacing=Spacing.SM,
                            vertical_alignment="center",
                            children=[
                                Icon(Icons.NAVIGATION, key=f"{key}_stats_icon",
                                     size=20, color=Theme.primary),
                                Text("Screens pushed this session",
                                     key=f"{key}_stats_label", size=13,
                                     color=Theme.text_secondary, expand=1),
                                Badge(visits.value,
                                      key=f"{key}_stats_badge",
                                      child=Text(
                                          str(visits.value),
                                          key=f"{key}_stats_value",
                                          size=15, weight=700,
                                          color=Theme.text)),
                            ],
                        ),
                        Text("The stack is "
                             f"{router.stack_size} deep right now.",
                             key=f"{key}_stack_note", size=12,
                             color=Theme.text_secondary),
                    ],
                ),
            ),
        ],
    )


def item_screen(page, params=None):
    """The pushed screen: receives params and pops itself."""
    params = dict(params or {})
    index = params.get("index", 1)
    via = params.get("via", "slide_left")
    page.bgcolor = Theme.background
    page.add(Column(
        key="pd_pg_item",
        expand=1,
        children=[
            AppBar(title=f"Item {index}", key="pd_pg_item_bar", leading=Icon(
                Icons.BACK, key="pd_pg_item_back", size=22,
                color=Theme.text).on_click(lambda _e: router.pop())),
            Column(
                key="pd_pg_item_body",
                spacing=Spacing.LG,
                expand=1,
                style={"padding": EdgeInsets(
                    left=Spacing.GUTTER, right=Spacing.GUTTER,
                    top=Spacing.LG, bottom=Spacing.LG).to_dict()},
                children=[
                    Card(
                        key="pd_pg_item_card",
                        padding=Spacing.XL,
                        child=Column(
                            key="pd_pg_item_card_col",
                            spacing=Spacing.SM,
                            children=[
                                Icon(Icons.LAYERS,
                                     key="pd_pg_item_icon", size=40,
                                     color=Theme.primary),
                                Text(f"You pushed item {index}",
                                     key="pd_pg_item_title", size=20,
                                     weight=700, color=Theme.text),
                                Text(f"Transition used: {via}",
                                     key="pd_pg_item_via", size=13,
                                     color=Theme.text_secondary),
                                Text(f"Params arrive as a dict: {params}",
                                     key="pd_pg_item_params", size=12,
                                     color=Theme.text_secondary),
                            ],
                        ),
                    ),
                    Button("Pop back", key="pd_pg_item_pop", variant="tonal",
                           icon=Icons.BACK, full_width=True
                           ).on_click(lambda _e: router.pop()),
                ],
            ),
        ],
    ))


from app.data.playground import PlaygroundDemo  # noqa: E402

DEMO = PlaygroundDemo(
    id="navigation",
    title="Navigation",
    blurb="Stack pushes with parameters, transitions and back handling.",
    icon="layers",
    tags=("router", "push", "back"),
    build=build,
    routes=("playground/item",),
)
