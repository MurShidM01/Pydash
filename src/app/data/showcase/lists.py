"""List, tile and card demos — the workhorses of every screen."""

from __future__ import annotations

from pydrud import (
    Card, CheckboxListTile, Colors, Column, Container, Divider,
    ExpansionTile, Icon, Icons, InfoCard, ListTile, ListView, NavigationTile,
    Radius, RadioListTile, ResponsiveGrid, Row, SettingsTile, Skeleton,
    Spacing, StatCard, SwitchListTile, Text, Theme, Widget,
)

from app.runtime import refresh
from app.state import State

__all__ = ["CATEGORY"]

#: Interactive state.
wifi_on = State(True, name="tile_wifi")
sync_on = State(False, name="tile_sync")
checked_tasks = State(("Build",), name="tile_tasks")
plan = State("Pro", name="tile_plan")
expanded_faq = State(0, name="tile_faq")

FAQS = (
    ("What is Pydash?",
     "A companion app that renders your Pydrud project live while you edit "
     "it — no APK rebuilds."),
    ("Does it run my Python?",
     "No. Your code runs on your computer via `pydrud dev`; the phone "
     "renders the UI and forwards taps back."),
    ("What happens on save?",
     "The dev server re-renders, diffs the trees, and Pydash applies a "
     "tiny patch — usually in milliseconds."),
)


def _tiles(key: str) -> Widget:
    return Card(
        key=f"{key}_card",
        padding=0,
        child=Column(
            key=f"{key}_col",
            children=[
                ListTile("Plain tile", key=f"{key}_plain",
                         subtitle="Title and subtitle, nothing else",
                         leading=Icons.INFO),
                Divider(key=f"{key}_d1"),
                ListTile("With trailing icon", key=f"{key}_trailing",
                         subtitle="Chevron hint for navigation",
                         leading=Icons.LAYERS,
                         trailing=Icons.CHEVRON_RIGHT,
                         on_click=lambda _e: _noop()),
                Divider(key=f"{key}_d2"),
                ListTile("Three-line tile", key=f"{key}_three",
                         subtitle="The subtitle can wrap onto a second "
                                  "line when there is a story to tell",
                         leading=Icons.FILE, three_line=True),
                Divider(key=f"{key}_d3"),
                ListTile("Dense tile", key=f"{key}_dense",
                         subtitle="Compact vertical rhythm", dense=True,
                         leading=Icons.LIST),
            ],
        ),
    )


def _noop():
    pass


def _control_tiles(key: str) -> Widget:
    return Card(
        key=f"{key}_card",
        padding=0,
        child=Column(
            key=f"{key}_col",
            children=[
                SwitchListTile("Wi-Fi", key=f"{key}_wifi",
                               control_key=f"{key}_wifi_switch",
                               value=wifi_on.value,
                               on_change=_set_wifi),
                Divider(key=f"{key}_d1"),
                CheckboxListTile("Background sync", key=f"{key}_sync",
                                 control_key=f"{key}_sync_box",
                                 value=sync_on.value,
                                 on_change=_set_sync),
                Divider(key=f"{key}_d2"),
                RadioListTile("Starter (free)", key=f"{key}_plan_free",
                              control_key=f"{key}_radio_free",
                              group="plan", value="Starter",
                              selected=plan.value == "Starter",
                              on_change=_set_plan("Starter")),
                RadioListTile("Pro", key=f"{key}_plan_pro",
                              control_key=f"{key}_radio_pro",
                              group="plan", value="Pro",
                              selected=plan.value == "Pro",
                              on_change=_set_plan("Pro")),
            ],
        ),
    )


def _set_wifi(event):
    wifi_on.value = bool(event.get("value", False))
    refresh()


def _set_sync(event):
    sync_on.value = bool(event.get("value", False))
    refresh()


def _set_plan(value: str):
    def handler(event):
        plan.value = str(event.get("value", value)) or value
        refresh()
    return handler


def _expansion(key: str) -> Widget:
    tiles = []
    for index, (question, answer) in enumerate(FAQS):
        tiles.append(ExpansionTile(
            question, key=f"{key}_tile{index}",
            subtitle=None if index else "Tap to expand",
            leading=Icons.HELP,
            expanded=expanded_faq.value == index,
            children=[
                Text(answer, key=f"{key}_answer{index}", size=13,
                     color=Theme.text_secondary),
            ],
            on_expand=_open_faq(index),
        ))
    return Column(key=f"{key}_col", spacing=Spacing.SM, children=tiles)


def _open_faq(index: int):
    def handler(_event):
        expanded_faq.value = 0 if expanded_faq.value == index else index
        refresh()
    return handler


def _preset_cards(key: str) -> Widget:
    return ResponsiveGrid(
        key=f"{key}_grid",
        min_item_width=150,
        max_columns=2,
        spacing=Spacing.SM,
        children=[
            StatCard("Widgets", 140, key=f"{key}_stat_widgets",
                     icon=Icons.LAYERS, trend="+8 this week"),
            StatCard("Preview lag", "42ms", key=f"{key}_stat_lag",
                     icon=Icons.TIMER, trend="+fast"),
            InfoCard("InfoCard", "Icon, title and body in a themed card.",
                     key=f"{key}_info", icon=Icons.INFO),
            InfoCard("Error look", "Same composition, different accent.",
                     key=f"{key}_info_err", icon=Icons.WARNING,
                     color=Colors.WARNING),
        ],
    )


def _settings_tiles(key: str) -> Widget:
    return Card(
        key=f"{key}_card",
        padding=0,
        child=Column(
            key=f"{key}_col",
            children=[
                SettingsTile("Project", value="my-pydrud-app",
                             key=f"{key}_project", leading=Icons.FOLDER),
                Divider(key=f"{key}_d1"),
                SettingsTile("Pydrud", value="2.0.2",
                             key=f"{key}_version", leading=Icons.PYTHON),
                Divider(key=f"{key}_d2"),
                NavigationTile("Open component catalog",
                               key=f"{key}_nav", leading=Icons.GRID),
            ],
        ),
    )


def _loading_lists(key: str) -> Widget:
    return ListView(
        key=f"{key}_list",
        spacing=Spacing.MD,
        children=[
            Row(key=f"{key}_row1", spacing=Spacing.MD,
                vertical_alignment="center", children=[
                    Container(key=f"{key}_av1", width=40, height=40,
                              border_radius=Radius.PILL,
                              bg=Theme.surface_variant),
                    Column(key=f"{key}_col1", spacing=6, expand=1, children=[
                        Skeleton(key=f"{key}_l1", width="70%", height=14),
                        Skeleton(key=f"{key}_l2", width="45%", height=12),
                    ]),
                ]),
            Skeleton(key=f"{key}_l3", width="match", height=14),
            Skeleton(key=f"{key}_l4", width="match", height=14),
            Skeleton(key=f"{key}_l5", width="60%", height=14),
        ],
    )


from app.data.catalog import Category, Demo  # noqa: E402

CATEGORY = Category(
    id="lists",
    name="Lists & cards",
    icon="list",
    blurb="ListTiles, control tiles, expansion panels and preset cards.",
    demos=(
        Demo(id="tiles", title="ListTile variants",
             description="Plain, trailing, three-line and dense rows.",
             build=_tiles, tags=("listtile", "row", "dense")),
        Demo(id="controls", title="Control tiles",
             description="Switch, checkbox and radio list tiles in one "
                         "group.",
             build=_control_tiles, tags=("switch", "checkbox", "radio")),
        Demo(id="expansion", title="Expansion panels",
             description="Accordion tiles revealing extra content.",
             build=_expansion, tags=("expand", "accordion", "faq")),
        Demo(id="cards", title="Preset cards",
             description="StatCard and InfoCard compositions.",
             build=_preset_cards, tags=("statcard", "infocard", "card")),
        Demo(id="settings", title="Settings & navigation tiles",
             description="The tiles settings screens are made of.",
             build=_settings_tiles, tags=("settings", "navigation")),
        Demo(id="skeletons", title="Loading skeletons",
             description="Shimmering placeholders while content loads.",
             build=_loading_lists, tags=("skeleton", "loading", "shimmer")),
    ),
)
