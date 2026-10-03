"""Layout, spacing and responsive demos."""

from __future__ import annotations

from pydrud import (
    Colors, Column, Container, Divider, Icon, Icons, Radius, Responsive,
    ResponsiveBuilder, ResponsiveGrid, Row, SafeArea, ShowWhen, Spacing,
    Text, Theme, Widget,
)

from pydrud import AdaptiveLayout, MediaQuery

__all__ = ["CATEGORY"]


def _spacing_scale(key: str) -> Widget:
    steps = (("XXS", Spacing.XXS), ("XS", Spacing.XS), ("SM", Spacing.SM),
             ("MD", Spacing.MD), ("LG", Spacing.LG), ("XL", Spacing.XL),
             ("XXL", Spacing.XXL), ("HUGE", Spacing.HUGE))
    rows = []
    for index, (name, value) in enumerate(steps):
        rows.append(Row(
            key=f"{key}_row{index}",
            spacing=Spacing.SM,
            vertical_alignment="center",
            children=[
                Text(name, key=f"{key}_name{index}", size=11, weight=700,
                     color=Theme.text_secondary, expand=1),
                Container(
                    key=f"{key}_bar{index}",
                    width=value * 4,
                    height=10,
                    border_radius=Radius.XS,
                    bg=Colors.mix(Theme.primary, Theme.secondary,
                                  index / len(steps)),
                ),
                Text(f"{value}dp", key=f"{key}_val{index}", size=11,
                     color=Theme.text_secondary),
            ],
        ))
    return Column(key=f"{key}_col", spacing=Spacing.SM, children=rows)


def _grid(key: str) -> Widget:
    tiles = []
    for index in range(6):
        tiles.append(Container(
            key=f"{key}_tile{index}",
            height=64,
            border_radius=Radius.MD,
            bg=Colors.mix(Theme.primary, Theme.secondary, index / 6),
            alignment="center",
            child=Text(str(index + 1), key=f"{key}_tile_label{index}",
                       size=15, weight=700, color=Colors.WHITE),
        ))
    return Column(
        key=f"{key}_col",
        spacing=Spacing.SM,
        children=[
            ResponsiveGrid(key=f"{key}_grid", min_item_width=110,
                           max_columns=3, spacing=Spacing.SM,
                           children=tiles),
            Text(f"Columns right now: {ResponsiveGrid(key=f'{key}_probe').columns} "
                 "— rotate or resize and the grid reflows.",
                 key=f"{key}_note", size=12,
                 color=Theme.text_secondary),
        ],
    )


def _adaptive(key: str) -> Widget:
    info = MediaQuery.info()

    def compact():
        return Column(key=f"{key}_compact", spacing=Spacing.XS, children=[
            Text("Compact", key=f"{key}_compact_t", size=14, weight=700,
                 color=Theme.text),
            Text("Stacked cards for phone widths.",
                 key=f"{key}_compact_s", size=12,
                 color=Theme.text_secondary),
        ])

    def medium():
        return Row(key=f"{key}_medium", spacing=Spacing.LG,
                   vertical_alignment="center", children=[
                       Text("Medium", key=f"{key}_medium_t", size=14,
                            weight=700, color=Theme.text),
                       Text("Side-by-side from 600dp.",
                            key=f"{key}_medium_s", size=12,
                            color=Theme.text_secondary),
                   ])

    def expanded():
        return Row(key=f"{key}_expanded", spacing=Spacing.LG,
               vertical_alignment="center", children=[
                   Icon(Icons.DASHBOARD, key=f"{key}_expanded_i", size=20,
                        color=Theme.primary),
                   Text("Expanded", key=f"{key}_expanded_t", size=14,
                        weight=700, color=Theme.text),
                   Text("A third arrangement past 840dp.",
                        key=f"{key}_expanded_s", size=12,
                        color=Theme.text_secondary),
               ])

    return Column(
        key=f"{key}_col",
        spacing=Spacing.MD,
        children=[
            AdaptiveLayout(compact=compact(), medium=medium(),
                           expanded=expanded(), key=f"{key}_adaptive"),
            Divider(key=f"{key}_div"),
            _metrics_table(key),
        ],
    )


def _metrics_table(key: str) -> Widget:
    info = MediaQuery.info()
    rows = (
        ("Window", f"{info.width:.0f} × {info.height:.0f} dp"),
        ("Breakpoint", str(info.breakpoint)),
        ("Orientation", str(info.orientation)),
        ("Density", f"{getattr(info, 'density', 0):.2f}"),
        ("Smallest width", f"{getattr(info, 'smallest_width', 0):.0f} dp"),
    )
    return Column(
        key=f"{key}_metrics",
        spacing=Spacing.XS,
        children=[
            Row(key=f"{key}_mrow{index}", spacing=Spacing.SM,
                vertical_alignment="center", children=[
                    Text(label, key=f"{key}_mlabel{index}", size=12,
                         color=Theme.text_secondary, expand=1),
                    Text(value, key=f"{key}_mvalue{index}", size=12,
                         weight=600, color=Theme.text),
                ])
            for index, (label, value) in enumerate(rows)
        ],
    )


def _show_when(key: str) -> Widget:
    return Column(
        key=f"{key}_col",
        spacing=Spacing.MD,
        children=[
            ShowWhen(
                Container(
                    key=f"{key}_wide_banner",
                    width="match",
                    padding=Spacing.MD,
                    border_radius=Radius.MD,
                    bg=Colors.with_opacity(Theme.primary, 0.12),
                    child=Text("This panel only exists at ≥ 600dp "
                               "(medium window).",
                               key=f"{key}_wide_text", size=13,
                               color=Theme.text),
                ),
                min_width=600,
                key=f"{key}_show_wide",
            ),
            Container(
                key=f"{key}_always",
                width="match",
                padding=Spacing.MD,
                border_radius=Radius.MD,
                bg=Theme.surface_variant,
                child=Text("This one always renders. On a phone you see "
                           "only it; unfold a foldable or rotate and the "
                           "wide panel appears.",
                           key=f"{key}_always_text", size=13,
                           color=Theme.text),
            ),
        ],
    )


def _stack(key: str) -> Widget:
    return Container(
        key=f"{key}_stage",
        width="match",
        height=180,
        border_radius=Radius.LG,
        bg=Theme.surface_variant,
        style={"position": "relative"},
        child=Container(
            key=f"{key}_holder",
            height=180,
            child=Container(
                key=f"{key}_badge_tile",
                width=120,
                height=120,
                border_radius=Radius.LG,
                bg=Theme.primary,
                alignment="center",
                style={"position": "absolute", "left": 24, "top": 30},
                child=Icon(Icons.LAYERS, key=f"{key}_stack_icon", size=40,
                           color=Colors.WHITE),
            ),
        ),
    )


from app.data.catalog import Category, Demo  # noqa: E402

CATEGORY = Category(
    id="layout",
    name="Layout & responsive",
    icon="dashboard",
    blurb="The spacing scale, grids, adaptive layouts and media queries.",
    demos=(
        Demo(id="spacing", title="Spacing scale",
             description="The 4dp rhythm every Pydrud layout is built on.",
             build=_spacing_scale, tags=("spacing", "scale", "padding")),
        Demo(id="grid", title="Responsive grid",
             description="Column count computed from the live window "
                         "width.",
             build=_grid, tags=("grid", "columns", "responsivegrid")),
        Demo(id="adaptive", title="Adaptive layouts",
             description="Different trees per window-size class, plus the "
                         "live metrics powering them.",
             build=_adaptive, tags=("adaptive", "breakpoint", "mediaquery")),
        Demo(id="showwhen", title="Conditional widgets",
             description="ShowWhen renders a subtree only when the query "
                         "matches.",
             build=_show_when, tags=("showwhen", "conditional", "wide")),
        Demo(id="stack", title="Stacks & positioning",
             description="Children layered with absolute offsets.",
             build=_stack, tags=("stack", "positioned", "overlay")),
    ),
)
