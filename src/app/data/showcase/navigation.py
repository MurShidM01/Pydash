"""Navigation widget demos — tabs, bars, rails, drawers and search."""

from __future__ import annotations

from pydrud import (
    Colors, Column, Container, Divider, Icon, Icons, ListTile, NavItem,
    Radius, Row, SafeArea, SearchBar, SegmentedButton, Spacing, Tab, Tabs,
    Text, Theme, Widget,
)
from pydrud import BottomNavigationBar, Drawer, NavigationRail

from app.runtime import refresh
from app.state import State

__all__ = ["CATEGORY"]

#: Interactive state.
tab = State(0, name="nav_tab")
dest = State(0, name="nav_dest")
rail = State(0, name="nav_rail")
search_text = State("", name="nav_search")

TAB_BODIES = (
    "Tabs keep only the selected page's content alive — like a lazy "
    "ViewPager.",
    "The indicator can be a line, pill or dot; labels can sit beside or "
    "under icons.",
    "Scrollable mode fits any number of tabs.",
)
DESTINATIONS = (
    ("Home", Icons.HOME, "The dashboard you came from"),
    ("Search", Icons.SEARCH, "Find anything in the project"),
    ("Profile", Icons.PERSON, "Your developer identity"),
)


def _tabs(key: str) -> Widget:
    return Tabs(
        [
            Tab("Overview", icon=Icons.DASHBOARD,
                content=_tab_body(key, 0)),
            Tab("Indicator", icon=Icons.STYLE if hasattr(Icons, "STYLE")
                else Icons.PALETTE, content=_tab_body(key, 1)),
            Tab("Scrollable", icon=Icons.SORT,
                content=_tab_body(key, 2)),
        ],
        key=f"{key}_tabs",
        selected=tab.value,
        indicator="pill",
        mode="fixed",
        on_change=_set_tab,
    )


def _tab_body(key: str, index: int) -> Widget:
    return Container(
        key=f"{key}_body{index}",
        width="match",
        padding=Spacing.MD,
        border_radius=Radius.MD,
        bg=Theme.surface_variant,
        child=Text(TAB_BODIES[index], key=f"{key}_text{index}", size=13,
                   color=Theme.text),
    )


def _set_tab(event):
    try:
        tab.value = int(event.get("value", tab.value))
    except (TypeError, ValueError):
        return
    refresh()


def _bottom_bar(key: str) -> Widget:
    body = DESTINATIONS[dest.value]
    return Column(
        key=f"{key}_col",
        spacing=Spacing.MD,
        children=[
            Container(
                key=f"{key}_stage",
                width="match",
                padding=Spacing.XL,
                border_radius=Radius.MD,
                bg=Theme.surface_variant,
                child=Column(
                    key=f"{key}_stage_col",
                    spacing=Spacing.XS,
                    horizontal_alignment="center",
                    children=[
                        Icon(body[1], key=f"{key}_stage_icon", size=30,
                             color=Theme.primary),
                        Text(body[0], key=f"{key}_stage_title", size=16,
                             weight=700, color=Theme.text),
                        Text(body[2], key=f"{key}_stage_sub", size=13,
                             color=Theme.text_secondary,
                             text_align="center"),
                    ],
                ),
            ),
            BottomNavigationBar(
                [NavItem(name, icon=icon, badge=None)
                 for name, icon, _ in DESTINATIONS],
                key=f"{key}_bar",
                selected=dest.value,
                on_change=_set_dest,
                height=62,
                radius=18,
                floating=True,
                margin=10,
            ),
            Text("Pydash's own main navigation is the same widget — this "
                 "bar is a second, fully configured instance.",
                 key=f"{key}_note", size=12,
                 color=Theme.text_secondary, text_align="center"),
        ],
    )


def _set_dest(event):
    try:
        dest.value = int(event.get("value", dest.value))
    except (TypeError, ValueError):
        return
    refresh()


def _rail(key: str) -> Widget:
    return Container(
        key=f"{key}_stage",
        width="match",
        height=230,
        border_radius=Radius.MD,
        bg=Theme.surface_variant,
        child=Row(
            key=f"{key}_row",
            children=[
                NavigationRail(
                    [NavItem(name, icon=icon)
                     for name, icon, _ in DESTINATIONS[:3]],
                    key=f"{key}_rail",
                    selected=rail.value,
                    on_change=_set_rail,
                ),
                Container(
                    key=f"{key}_body",
                    expand=1,
                    padding=Spacing.LG,
                    child=Column(
                        key=f"{key}_body_col",
                        spacing=Spacing.XS,
                        children=[
                            Text(DESTINATIONS[rail.value][0],
                                 key=f"{key}_body_title", size=15,
                                 weight=700, color=Theme.text),
                            Text("Rails are for tablets and landscape. "
                                 "Pydash's shell swaps its bottom bar for "
                                 "one automatically on wide screens.",
                                 key=f"{key}_body_sub", size=12,
                                 color=Theme.text_secondary),
                        ],
                    ),
                ),
            ],
        ),
    )


def _set_rail(event):
    try:
        rail.value = int(event.get("value", rail.value))
    except (TypeError, ValueError):
        return
    refresh()


def _search(key: str) -> Widget:
    query = search_text.value.strip().lower()
    fruits = ["Animator", "Badge", "Canvas", "Dropdown", "Expansion",
              "Fab", "Gesture", "Hero", "Icon", "Json", "Keypad"]
    hits = [f for f in fruits if query in f.lower()]
    results = Column(
        key=f"{key}_results",
        spacing=Spacing.XS,
        children=[
            ListTile(f, key=f"{key}_hit{index}", leading=Icons.CHEVRON_RIGHT,
                     dense=True)
            for index, f in enumerate(hits)
        ],
    ) if hits else Text("No matches", key=f"{key}_empty", size=13,
                        color=Theme.text_secondary)
    return Column(
        key=f"{key}_col",
        spacing=Spacing.MD,
        children=[
            SearchBar(search_text.value, key=f"{key}_search",
                      hint="Search widgets…",
                      on_change=_set_search),
            results,
        ],
    )


def _set_search(event):
    search_text.value = str(event.get("value", ""))
    refresh()


def _drawer(key: str) -> Widget:
    from app.runtime import current

    def open_it(_event):
        app = current()
        if app is not None:
            app.page.open_drawer("start")

    return Column(
        key=f"{key}_col",
        spacing=Spacing.MD,
        children=[
            Text("Drawers are declared on the Scaffold and opened from "
                 "Python. This button opens Pydash's own drawer.",
                 key=f"{key}_hint", size=13,
                 color=Theme.text_secondary),
            Container(
                key=f"{key}_mock",
                width="match",
                height=110,
                border_radius=Radius.MD,
                bg=Theme.surface_variant,
                child=Row(
                    key=f"{key}_mock_row",
                    children=[
                        Container(
                            key=f"{key}_mock_panel",
                            width=170,
                            height="match",
                            border_radius=Radius.MD,
                            bg=Theme.surface,
                            padding=Spacing.MD,
                            child=Column(
                                key=f"{key}_mock_col",
                                spacing=Spacing.SM,
                                children=[
                                    Text("Drawer", key=f"{key}_mock_title",
                                         size=14, weight=700,
                                         color=Theme.text),
                                    Text("Slides over the body",
                                         key=f"{key}_mock_sub", size=12,
                                         color=Theme.text_secondary),
                                ],
                            ),
                        ),
                    ],
                ),
            ),
        ],
    )


from app.data.catalog import Category, Demo  # noqa: E402

CATEGORY = Category(
    id="navigation",
    name="Navigation",
    icon="explore",
    blurb="Tabs, bottom bars, navigation rails, drawers and search.",
    demos=(
        Demo(id="tabs", title="Tabs",
             description="A pill-indicator tab bar with lazy content.",
             build=_tabs, tags=("tabs", "tabbar", "indicator")),
        Demo(id="bottom", title="Bottom navigation",
             description="A floating, rounded bar with badges and a live "
                         "content pane.",
             build=_bottom_bar, tags=("navbar", "bottom", "destinations")),
        Demo(id="rail", title="Navigation rail",
             description="The vertical form wide screens switch to.",
             build=_rail, tags=("rail", "tablet", "sidebar")),
        Demo(id="search", title="Search",
             description="SearchBar with live-filtered results.",
             build=_search, tags=("search", "filter")),
        Demo(id="drawer", title="Drawer",
             description="A navigation drawer mock plus a button that opens "
                         "the app's real one.",
             build=_drawer, tags=("drawer", "hamburger", "sidebar")),
    ),
)
