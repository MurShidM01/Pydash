"""Kitchen sink — tabs, search and segmented controls in one screen."""

from __future__ import annotations

from pydrud import (
    Card, Column, Container, Divider, Icon, Icons, ListTile, Radius, Row,
    SearchBar, SegmentedButton, Spacing, Tab, Tabs, Text, Theme, Widget,
)

from app.runtime import refresh
from app.state import State

__all__ = ["DEMO"]

query = State("", name="pg_kitchen_query")
tab = State(0, name="pg_kitchen_tab")
density = State(1, name="pg_kitchen_density")

CATALOG = (
    ("Scaffold", "app_bar + body + bottom navigation + FAB"),
    ("AppBar", "title, leading and action slots"),
    ("Tabs", "lazy bodies with pill indicators"),
    ("SearchBar", "suggestions and clear button"),
    ("SegmentedButton", "single- or multi-choice rows"),
    ("ResponsiveGrid", "columns from window width"),
    ("SafeArea", "insets-aware padding"),
    ("ShowWhen", "conditional responsive subtrees"),
    ("Stepper", "wizard progress"),
    ("Skeleton", "loading placeholders"),
)


def build(key: str) -> Widget:
    text = query.value.strip().lower()
    hits = [item for item in CATALOG
            if not text or text in item[0].lower()
            or text in item[1].lower()]

    if tab.value == 0:
        body = _catalog_list(key, hits)
    elif tab.value == 1:
        body = _catalog_grid(key, hits)
    else:
        body = _catalog_cards(key, hits)

    return Column(
        key=f"{key}_col",
        spacing=Spacing.LG,
        children=[
            SearchBar(query.value, key=f"{key}_search",
                      hint="Search widgets…",
                      suggestions=["Scaffold", "Tabs", "SafeArea"],
                      on_change=_set_query),
            SegmentedButton(["List", "Grid", "Cards"], key=f"{key}_density",
                            selected=density.value
                            ).on_change(_set_density),
            Tabs(
                [
                    Tab("All", icon=Icons.APPS, content=body),
                    Tab("Found", icon=Icons.SEARCH,
                        content=_found_pane(key, hits)),
                    Tab("About", icon=Icons.INFO,
                        content=_about_pane(key)),
                ],
                key=f"{key}_tabs",
                selected=tab.value,
                indicator="pill",
                on_change=_set_tab,
            ),
        ],
    )


def _set_query(event):
    query.value = str(event.get("value", ""))
    refresh()


def _set_density(event):
    try:
        density.value = int(event.get("value", density.value))
    except (TypeError, ValueError):
        return
    refresh()


def _set_tab(event):
    try:
        tab.value = int(event.get("value", tab.value))
    except (TypeError, ValueError):
        return
    refresh()


def _catalog_list(key: str, hits) -> Widget:
    if not hits:
        return _no_hits(key)
    rows: list[Widget] = []
    for index, (name, desc) in enumerate(hits):
        if index:
            rows.append(Divider(key=f"{key}_ldiv{index}"))
        rows.append(ListTile(name, key=f"{key}_lrow{index}", subtitle=desc,
                             leading=Icons.CHEVRON_RIGHT, dense=True))
    return Card(
        key=f"{key}_list",
        padding=0,
        child=Column(key=f"{key}_list_col", children=rows),
    )


def _catalog_grid(key: str, hits) -> Widget:
    from pydrud import ResponsiveGrid

    if not hits:
        return _no_hits(key)
    return ResponsiveGrid(
        key=f"{key}_grid",
        min_item_width=120,
        max_columns=3,
        spacing=Spacing.SM,
        children=[
            Container(
                key=f"{key}_gtile{i}",
                height=64,
                border_radius=Radius.MD,
                bg=Theme.surface_variant,
                alignment="center",
                child=Text(name, key=f"{key}_gtile_t{i}", size=12,
                           weight=600, color=Theme.text),
            )
            for i, (name, _desc) in enumerate(hits)
        ],
    )


def _catalog_cards(key: str, hits) -> Widget:
    if not hits:
        return _no_hits(key)
    return Column(
        key=f"{key}_cards",
        spacing=Spacing.SM,
        children=[
            Card(
                key=f"{key}_card{i}",
                padding=Spacing.MD,
                child=Row(
                    key=f"{key}_card{i}_row",
                    spacing=Spacing.MD,
                    vertical_alignment="center",
                    children=[
                        Icon(Icons.LAYERS, key=f"{key}_card{i}_icon",
                             size=18, color=Theme.primary),
                        Column(
                            key=f"{key}_card{i}_col",
                            spacing=2,
                            expand=1,
                            children=[
                                Text(name, key=f"{key}_card{i}_t", size=14,
                                     weight=600, color=Theme.text),
                                Text(desc, key=f"{key}_card{i}_d", size=12,
                                     color=Theme.text_secondary),
                            ],
                        ),
                    ],
                ),
            )
            for i, (name, desc) in enumerate(hits)
        ],
    )


def _no_hits(key: str) -> Widget:
    return Container(
        key=f"{key}_empty",
        width="match",
        padding=Spacing.XL,
        border_radius=Radius.MD,
        bg=Theme.surface_variant,
        child=Column(
            key=f"{key}_empty_col",
            spacing=Spacing.XS,
            horizontal_alignment="center",
            children=[
                Icon(Icons.SEARCH, key=f"{key}_empty_icon", size=30,
                     color=Theme.text_secondary),
                Text("No widgets match", key=f"{key}_empty_t", size=14,
                     weight=600, color=Theme.text),
                Text("Try a shorter query.", key=f"{key}_empty_s", size=12,
                     color=Theme.text_secondary),
            ],
        ),
    )


def _found_pane(key: str, hits) -> Widget:
    return Container(
        key=f"{key}_found",
        width="match",
        padding=Spacing.LG,
        border_radius=Radius.MD,
        bg=Theme.surface_variant,
        child=Column(
            key=f"{key}_found_col",
            spacing=Spacing.XS,
            children=[
                Text(f"{len(hits)} of {len(CATALOG)} widgets match "
                     f"'{query.value or '…'}'.",
                     key=f"{key}_found_t", size=14, weight=600,
                     color=Theme.text),
                Text("The list, grid and card panes all read the same "
                     "state — one query, three presentations.",
                     key=f"{key}_found_s", size=12,
                     color=Theme.text_secondary),
            ],
        ),
    )


def _about_pane(key: str) -> Widget:
    return Container(
        key=f"{key}_about",
        width="match",
        padding=Spacing.LG,
        border_radius=Radius.MD,
        bg=Theme.surface_variant,
        child=Column(
            key=f"{key}_about_col",
            spacing=Spacing.XS,
            children=[
                Text("One screen, five widgets cooperating",
                     key=f"{key}_about_t", size=14, weight=600,
                     color=Theme.text),
                Text("SearchBar filters, SegmentedButton picks a "
                     "presentation, Tabs host the panes and each pane "
                     "re-renders from shared State.",
                     key=f"{key}_about_s", size=12,
                     color=Theme.text_secondary),
            ],
        ),
    )


from app.data.playground import PlaygroundDemo  # noqa: E402

DEMO = PlaygroundDemo(
    id="kitchen",
    title="Kitchen Sink",
    blurb="Search, segmented controls and tabs driving shared state.",
    icon="apps",
    tags=("tabs", "search", "segmented"),
    build=build,
)
