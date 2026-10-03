"""Components — the interactive widget catalog.

An index of every showcase category with live search, opening onto a
per-category screen of hands-on demos. The catalog data lives in
:mod:`app.data.catalog`; this screen only presents it.
"""

from __future__ import annotations

from pydrud import (
    Card, Colors, Column, Container, Icon, Icons, Radius, ResponsiveGrid,
    Row, SearchField, Spacing, Text, Theme, Widget,
)

from app.data.catalog import CATEGORIES, search
from app.runtime import refresh, router
from app.state import catalog_query

__all__ = ["body", "category_screen"]


def body() -> list:
    query = catalog_query.value
    categories = search(query)
    sections: list[Widget] = [
        _search_bar(),
    ]
    if query and not categories:
        sections.append(_empty(query))
        return sections
    sections.append(ResponsiveGrid(
        key="pd_cat_grid",
        min_item_width=150,
        max_columns=2,
        spacing=Spacing.SM,
        children=[_category_card(category) for category in categories],
    ))
    sections.append(Text(f"{len(CATEGORIES)} categories · "
                         f"{sum(len(c.demos) for c in CATEGORIES)} live "
                         "demos — every widget the SDK ships.",
                         key="pd_cat_footnote", size=12,
                         color=Theme.text_secondary, text_align="center"))
    return sections


def _search_bar() -> Widget:
    return SearchField(catalog_query.value, key="pd_cat_search",
                       hint="Search widgets…",
                       ).on_change(_set_query)


def _set_query(event):
    catalog_query.value = str(event.get("value", ""))
    refresh()


def _empty(query: str) -> Widget:
    return Card(
        key="pd_cat_empty",
        padding=Spacing.XL,
        child=Column(
            key="pd_cat_empty_col",
            spacing=Spacing.SM,
            horizontal_alignment="center",
            children=[
                Icon(Icons.SEARCH, key="pd_cat_empty_icon", size=34,
                     color=Theme.text_secondary),
                Text(f"Nothing matches “{query}”",
                     key="pd_cat_empty_title", size=15, weight=600,
                     color=Theme.text),
                Text("Try “chip”, “theme”, “canvas” or “animation”.",
                     key="pd_cat_empty_hint", size=12,
                     color=Theme.text_secondary),
            ],
        ),
    )


def _category_card(category) -> Widget:
    return Card(
        key=category.key,
        padding=Spacing.LG,
        on_click=lambda _e, cat=category: router.push("category",
                                                      cat=cat.id),
        child=Column(
            key=f"{category.key}_col",
            spacing=Spacing.SM,
            children=[
                Row(
                    key=f"{category.key}_head",
                    spacing=Spacing.MD,
                    vertical_alignment="center",
                    children=[
                        Container(
                            key=f"{category.key}_icon_tile",
                            width=42,
                            height=42,
                            border_radius=Radius.MD,
                            bg=Colors.with_opacity(Theme.primary, 0.12),
                            alignment="center",
                            child=Icon(category.icon,
                                       key=f"{category.key}_icon", size=20,
                                       color=Theme.primary),
                        ),
                        Column(
                            key=f"{category.key}_head_col",
                            spacing=2,
                            expand=1,
                            children=[
                                Text(category.name,
                                     key=f"{category.key}_name", size=15,
                                     weight=700, color=Theme.text),
                                Text(f"{len(category.demos)} demos",
                                     key=f"{category.key}_count", size=12,
                                     color=Theme.text_secondary),
                            ],
                        ),
                        Icon(Icons.CHEVRON_RIGHT,
                             key=f"{category.key}_chevron", size=18,
                             color=Theme.text_secondary),
                    ],
                ),
                Text(category.blurb, key=f"{category.key}_blurb", size=12,
                     color=Theme.text_secondary),
            ],
        ),
    )


# ── category detail screen ─────────────────────────────────────────────────

def category_screen(page, params=None) -> None:
    """All demos inside one category."""
    params = dict(params or {})
    category_id = str(params.get("cat", ""))
    category = next((c for c in CATEGORIES if c.id == category_id), None)
    page.bgcolor = Theme.background
    if category is None:
        page.add(Column(key="pd_cat_missing", spacing=Spacing.LG, children=[
            Text("Unknown category", key="pd_cat_missing_t", size=16,
                 weight=700, color=Theme.text),
            Text("It may have been renamed.",
                 key="pd_cat_missing_s", size=13,
                 color=Theme.text_secondary),
        ]))
        return

    from app.components import page_body, section

    cards = []
    for demo in category.demos:
        cards.append(Card(
            key=demo.key,
            padding=Spacing.LG,
            child=Column(
                key=f"{demo.key}_screen_col",
                spacing=Spacing.MD,
                children=[
                    Text(demo.title, key=f"{demo.key}_t", size=15,
                         weight=700, color=Theme.text),
                    Text(demo.description, key=f"{demo.key}_d", size=12,
                         color=Theme.text_secondary)
                    if demo.description else Container(
                        key=f"{demo.key}_nod", height=0),
                    demo.build(demo.key) if demo.build else Container(
                        key=f"{demo.key}_nob", height=0),
                ],
            ),
        ))
    page.add(page_body(
        "pd_cat_detail",
        [
            section(category.name.upper(), "pd_cat_detail_sec",
                    subtitle=category.blurb),
            *cards,
        ],
    ))
