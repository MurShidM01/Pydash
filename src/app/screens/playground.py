"""Playground index — the signature Pydash experiences."""

from __future__ import annotations

from pydrud import (
    Card, Colors, Column, Container, Divider, Icon, Icons, Radius, Row,
    Spacing, Text, Theme, Widget,
)

from app.data.playground import DEMOS
from app.runtime import router

__all__ = ["body", "demo_screen"]


def body() -> list:
    cards = [_demo_card(demo) for demo in DEMOS]
    return [
        _intro(),
        Column(key="pd_pg_list", spacing=Spacing.SM, children=cards),
    ]


def _intro() -> Widget:
    return Container(
        key="pd_pg_intro",
        width="match",
        border_radius=Radius.XL,
        padding=Spacing.XL,
        style={
            "gradient": {
                "colors": [Colors.mix(Theme.primary, Theme.secondary, 0.0),
                           Colors.mix(Theme.primary, Theme.secondary, 0.7)],
                "direction": "diagonal",
            },
        },
        child=Row(
            key="pd_pg_intro_row",
            spacing=Spacing.LG,
            vertical_alignment="center",
            children=[
                Container(
                    key="pd_pg_intro_tile",
                    width=52,
                    height=52,
                    border_radius=Radius.PILL,
                    bg=Colors.with_opacity(Colors.WHITE, 0.18),
                    alignment="center",
                    child=Icon(Icons.ROCKET, key="pd_pg_intro_icon",
                               size=24, color=Colors.WHITE),
                ),
                Column(
                    key="pd_pg_intro_col",
                    spacing=2,
                    expand=1,
                    children=[
                        Text("Playground", key="pd_pg_intro_title", size=20,
                             weight=800, color=Colors.WHITE),
                        Text("Ten interactive framework demos — state, "
                             "theming, navigation, motion and more.",
                             key="pd_pg_intro_sub", size=12,
                             color=Colors.with_opacity(Colors.WHITE, 0.88)),
                    ],
                ),
            ],
        ),
    )


def _demo_card(demo) -> Widget:
    return Card(
        key=demo.key,
        padding=Spacing.LG,
        on_click=lambda _e, d=demo: router.push("demo", id=d.id),
        child=Row(
            key=f"{demo.key}_row",
            spacing=Spacing.MD,
            vertical_alignment="center",
            children=[
                Container(
                    key=f"{demo.key}_icon_tile",
                    width=44,
                    height=44,
                    border_radius=Radius.MD,
                    bg=Colors.with_opacity(Theme.primary, 0.12),
                    alignment="center",
                    child=Icon(demo.icon, key=f"{demo.key}_icon", size=21,
                               color=Theme.primary),
                ),
                Column(
                    key=f"{demo.key}_col",
                    spacing=2,
                    expand=1,
                    children=[
                        Text(demo.title, key=f"{demo.key}_t", size=15,
                             weight=700, color=Theme.text),
                        Text(demo.blurb, key=f"{demo.key}_b", size=12,
                             color=Theme.text_secondary),
                    ],
                ),
                Icon(Icons.CHEVRON_RIGHT, key=f"{demo.key}_chevron",
                     size=18, color=Theme.text_secondary),
            ],
        ),
    )


# ── demo detail screen ─────────────────────────────────────────────────────

def demo_screen(page, params=None) -> None:
    """One playground demo, full screen."""
    params = dict(params or {})
    demo = next((d for d in DEMOS if d.id == str(params.get("id", ""))),
                None)
    page.bgcolor = Theme.background
    from app.components import page_body

    if demo is None:
        page.add(page_body("pd_demo_missing", [
            Column(key="pd_demo_missing_col", spacing=Spacing.SM, children=[
                Text("Demo not found", key="pd_demo_missing_t", size=16,
                     weight=700, color=Theme.text),
                Text("It may have been renamed.",
                     key="pd_demo_missing_s", size=13,
                     color=Theme.text_secondary),
            ]),
        ]))
        return

    page.add(page_body(
        f"pd_demo_{demo.id}",
        [
            _demo_header(demo),
            demo.build(f"pd_demo_{demo.id}_body")
            if demo.build else Container(key="pd_demo_nob", height=0),
        ],
    ))


def _demo_header(demo) -> Widget:
    return Row(
        key=f"{demo.key}_header",
        spacing=Spacing.MD,
        vertical_alignment="center",
        children=[
            Container(
                key=f"{demo.key}_header_tile",
                width=40,
                height=40,
                border_radius=Radius.MD,
                bg=Colors.with_opacity(Theme.primary, 0.12),
                alignment="center",
                child=Icon(demo.icon, key=f"{demo.key}_header_icon",
                           size=19, color=Theme.primary),
            ),
            Column(
                key=f"{demo.key}_header_col",
                spacing=2,
                expand=1,
                children=[
                    Text(demo.title, key=f"{demo.key}_header_t", size=17,
                         weight=800, color=Theme.text),
                    Text(demo.blurb, key=f"{demo.key}_header_b", size=12,
                         color=Theme.text_secondary),
                ],
            ),
        ],
    )
