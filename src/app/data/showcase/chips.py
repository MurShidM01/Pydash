"""Chip, badge and banner demos — compact entities, counts and alerts."""

from __future__ import annotations

from pydrud import (
    ActionChip, AssistChip, Avatar, Badge, Banner, ChoiceChip, Colors,
    Column, Container, Divider, Icon, Icons, InputChip, Radius, Row,
    Spacing, Text, Theme, Widget,
)

from app.runtime import refresh
from app.state import State

__all__ = ["CATEGORY"]

#: Live state for the interactive chip demos.
picked = State(("Dart",), name="chip_picked")
skills = State(("Python", "Pydrud"), name="chip_skills")
badge_count = State(3, name="badge_count")
dismissed = State(False, name="banner_dismissed")

ALL_SKILLS = ("Python", "Pydrud", "Dart", "Kotlin", "Swift", "Rust", "Go")
FLAVOURS = ("Mint", "Cocoa", "Berry")


def _variants(key: str) -> Widget:
    return Column(
        key=f"{key}_col",
        spacing=Spacing.MD,
        children=[
            Row(key=f"{key}_assist", spacing=Spacing.XS, children=[
                AssistChip("Assist", key=f"{key}_assist_chip",
                           icon=Icons.ADD, on_click=_bump_badge),
                InputChip("Input", key=f"{key}_input_chip",
                          icon=Icons.PERSON, deletable=True,
                          on_delete=_drop_skill),
            ]),
            Row(key=f"{key}_suggest", spacing=Spacing.XS, children=[
                Container(key=f"{key}_pad", width=2),
                InputChip("someone@pydrud.dev", key=f"{key}_contact",
                          icon=Icons.EMAIL, deletable=True,
                          on_delete=_drop_skill),
            ]),
            Row(key=f"{key}_action", spacing=Spacing.XS, children=[
                ActionChip("Copy", key=f"{key}_copy", icon=Icons.COPY,
                           on_click=_bump_badge),
                ActionChip("Share", key=f"{key}_share", icon=Icons.SHARE,
                           on_click=_bump_badge),
            ]),
        ],
    )


def _filters(key: str) -> Widget:
    chips = []
    for flavour in FLAVOURS:
        selected = flavour in picked.value
        chips.append(ChoiceChip(flavour, key=f"{key}_{flavour.lower()}",
                                selected=selected,
                                on_change=_toggle_flavour(flavour)))
    chips.append(
        Suggestion("Try Yuzu", key=f"{key}_suggest",
                   icon=Icons.SPARKLE, on_click=_suggest))
    return Column(
        key=f"{key}_col",
        spacing=Spacing.MD,
        children=[
            Row(key=f"{key}_row", spacing=Spacing.XS, children=chips),
            Text("Selected: " + (", ".join(picked.value) or "none"),
                 key=f"{key}_label", size=13, weight=600,
                 color=Theme.primary),
        ],
    )


def Suggestion(label, *, key, icon, on_click):
    from pydrud import SuggestionChip

    return SuggestionChip(label, key=key, icon=icon, on_click=on_click)


def _toggle_flavour(flavour: str):
    def handler(_event):
        current = set(picked.value)
        if flavour in current:
            current.discard(flavour)
        else:
            current.add(flavour)
        picked.value = tuple(sorted(current))
        refresh()
    return handler


def _suggest(_event):
    current = set(picked.value)
    current.add("Yuzu")
    picked.value = tuple(sorted(current))
    refresh()


def _bump_badge(_event):
    badge_count.value += 1
    refresh()


def _drop_skill(_event):
    remaining = tuple(s for s in skills.value if s != "Dart")
    skills.value = remaining or ("Python",)
    refresh()


def _badges(key: str) -> Widget:
    count = badge_count.value
    return Row(
        key=f"{key}_row",
        spacing=Spacing.XL,
        horizontal_alignment="center",
        children=[
            Badge(count, key=f"{key}_count",
                  child=Icon(Icons.NOTIFICATIONS, key=f"{key}_bell_icon",
                             size=24, color=Theme.text)),
            Badge("NEW", key=f"{key}_text",
                  child=Avatar(initials="PY", key=f"{key}_avatar", size=44)),
            Badge(999, key=f"{key}_max",
                  child=Icon(Icons.MESSAGE, key=f"{key}_msg_icon", size=24,
                             color=Theme.text)),
            Icon(Icons.ADD_CIRCLE, key=f"{key}_bump", size=26,
                 color=Theme.primary).on_click(_bump_badge),
        ],
    )


def _banner(key: str) -> Widget:
    if dismissed.value:
        return Column(
            key=f"{key}_col",
            spacing=Spacing.MD,
            children=[
                Text("Banner dismissed. Tap below to bring it back.",
                     key=f"{key}_hint", size=13,
                     color=Theme.text_secondary),
                ActionChip("Show banner", key=f"{key}_restore",
                           icon=Icons.REFRESH, on_click=_restore),
            ],
        )
    return Banner(
        "This banner is a real Material banner — dismiss it or act on it.",
        key=f"{key}_banner", severity="info", icon=Icons.INFO,
        action="Act", on_action=_bump_badge, on_dismiss=_dismiss,
        dismissible=True,
    )


def _dismiss(_event):
    dismissed.value = True
    refresh()


def _restore(_event):
    dismissed.value = False
    badge_count.value = 0
    refresh()


from app.data.catalog import Category, Demo  # noqa: E402

CATEGORY = Category(
    id="chips",
    name="Chips & badges",
    icon="label",
    blurb="Compact entities, filter chips, counts and banners.",
    demos=(
        Demo(id="variants", title="Chip variants",
             description="Assist, input, suggestion and action chips.",
             build=_variants, tags=("chip", "assist", "input", "suggestion")),
        Demo(id="filters", title="Filter & choice chips",
             description="Selectable chips that report their state.",
             build=_filters, tags=("filter", "choice", "select")),
        Demo(id="badges", title="Badges",
             description="Counts and labels overlaid on icons and avatars. "
                         "Tap + to grow the count.",
             build=_badges, tags=("badge", "count", "avatar")),
        Demo(id="banner", title="Banners",
             description="Dismissible message strip with an action.",
             build=_banner, tags=("banner", "alert", "dismiss")),
    ),
)
