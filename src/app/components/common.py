"""The small, reusable pieces every Pydash screen is assembled from.

Nothing here knows about the preview protocol — these are the plain building
blocks (surfaces, headers, key/value lists, stat tiles, empty states and the
"how it works" steps) that give the whole app one consistent voice. Screens
import them from :mod:`app.components` and stay declarative.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional, Tuple, Union

from pydrud import (
    AppBar,
    CircularProgress,
    Column,
    Container,
    IconButton,
    Row,
    Text,
    Tokens,
    Tooltip,
    Widget,
)

from app import theme

__all__ = [
    "APP_BAR_HEIGHT", "app_bar", "bar_action", "card", "loading_panel",
    "meta_list", "notice_state", "section_header", "spinner", "stat_tile",
    "step_row",
]

#: The height every Pydash app bar is pinned to. Bars are *compact*: the
#: shared chrome stays out of the way of the content, and a fixed height keeps
#: Home, Scan, Preview and Settings pixel-identical instead of each bar
#: growing to fit whatever controls it happens to carry.
APP_BAR_HEIGHT = 52


# ── App bars ─────────────────────────────────────────────────────────────────


def app_bar(
    title: Union[str, Widget],
    *,
    leading: Optional[Widget] = None,
    actions: Optional[Iterable[Widget]] = None,
    key: str = "pd_bar",
) -> AppBar:
    """A compact, consistent top bar shared by every Pydash screen.

    The bar is dressed as a card along its bottom edge: the two bottom corners
    are rounded and a chrome outline is stroked straight onto that shape, so the
    border follows the corners. The outline is uniform, so the bar bleeds 2dp
    off the top and sides — that hides the outer edges and leaves the rule on
    the bottom edge alone.

    The bar's height comes from its tallest child, not from ``height`` (which is
    only a floor). A screen whose only control is a small icon would therefore
    get a visibly shorter bar than one carrying an action button, so the leading
    is wrapped in a full touch-target slot (:func:`_leading_slot`): every bar —
    with or without a leading, whatever the icon's own size — ends up the same
    height.
    """
    return AppBar(
        title=title,
        leading=_leading_slot(leading, key),
        actions=list(actions or []),
        density="compact",
        height=APP_BAR_HEIGHT,
        divider=False,
        style={**theme.chrome_outline(), **theme.rounded_edge(bottom=True),
               **theme.chrome_bleed(top=True)},
        key=key,
    )


def _leading_slot(leading: Optional[Widget], key: str) -> Optional[Widget]:
    """Reserve a full touch-target slot behind a bar's leading widget.

    An icon is drawn at its own size (~22dp) — shorter than a bar's action
    button — so a bar whose leading is the only control would collapse to the
    title's height. Sizing the slot to the shared ``touch_target`` token makes
    the leading and the actions equally tall, which is what keeps every app bar
    pixel-identical.
    """
    if leading is None:
        return None
    return Container(
        key=f"{key}_leading_slot",
        alignment="center",
        style={"minHeight": float(Tokens.touch_target)},
        child=leading,
    )


def bar_action(
    icon: str,
    label: str,
    handler,
    *,
    key: Optional[str] = None,
) -> Tooltip:
    """A compact icon button for an app bar, with a long-press tooltip.

    The button is ``size="sm"`` so it never dictates the bar height, and
    carries its label as the accessibility description.
    """
    return Tooltip(
        label,
        child=IconButton(
            icon,
            size="sm",
            semantics=label,
            key=key or f"pd_action_{label.lower().replace(' ', '_')}",
            on_click=lambda _e: handler(),
        ),
    )


# ── Surfaces ─────────────────────────────────────────────────────────────────


def card(
    child: Union[Widget, Iterable[Widget]],
    *,
    key: str = "pd_card",
    tint: bool = False,
    accent: bool = False,
    spacing: float = 0,
    on_click=None,
) -> Container:
    """A padded surface: ``tint=True`` uses the softer variant background.

    The caller passes either one widget or a list of widgets, which are
    stacked in a :class:`~pydrud.Column` so callers never repeat the layout
    boilerplate. ``accent=True`` outlines the card in the brand colour — the
    "featured"/active surface.
    """
    body: Widget = child
    if isinstance(child, (list, tuple)):
        body = Column(key=f"{key}_col", spacing=spacing,
                      children=list(child))
    klass = "pd-card-accent" if accent else (
        "pd-card-tint" if tint else "pd-card")
    surface = Container(
        key=key,
        class_=klass,
        width="match",
        style=theme.hairline(theme.primary() if accent else None),
        child=body,
    )
    if on_click is not None:
        surface.on_click(on_click)
    return surface


def section_header(
    title: str,
    *,
    caption: Optional[str] = None,
    action: Optional[Widget] = None,
    key: str = "pd_section",
) -> Column:
    """A section title with an optional overline and a trailing action.

    A short brand-coloured bar leads the title so sections scan as distinct
    blocks instead of blending into one another.
    """
    children: list[Widget] = []
    if caption:
        children.append(Text(caption, key=f"{key}_caption",
                             class_="pd-caption", max_lines=1))
    row: list[Widget] = [
        Container(key=f"{key}_accent", class_="pd-section-accent"),
        Text(title, key=f"{key}_title", class_="pd-h2", expand=1,
             max_lines=1),
    ]
    if action is not None:
        row.append(action)
    children.append(Row(key=f"{key}_row", spacing=8,
                        vertical_alignment="center",
                        main_axis_size="max", children=row))
    return Column(key=key, spacing=5, children=children)


# ── Key / value metadata ─────────────────────────────────────────────────────


def meta_list(
    items: Iterable[Tuple[Any, Any]],
    *,
    key: str = "pd_meta",
    mono: bool = False,
    spacing: float = 9,
) -> Column:
    """A quiet list of ``(label, value)`` rows — used for server & SDK info.

    With ``mono=True`` the values render in the monospace presentation, which
    suits host:port strings, session ids and versions.
    """
    rows: list[Widget] = []
    for index, (label, value) in enumerate(items):
        rows.append(Row(
            key=f"{key}_{index}",
            main_axis_size="max",
            vertical_alignment="center",
            spacing=14,
            children=[
                Text(str(label), key=f"{key}_{index}_k", class_="pd-meta-key",
                     max_lines=1, overflow="clip"),
                Text(str(value), key=f"{key}_{index}_v",
                     class_="pd-mono" if mono else "pd-meta-val",
                     text_align="right", expand=1, max_lines=1,
                     overflow="ellipsis"),
            ],
        ))
    return Column(key=key, spacing=spacing, children=rows)


# ── Stats ────────────────────────────────────────────────────────────────────


def stat_tile(
    value: Any,
    label: str,
    *,
    key: str = "pd_stat",
    accent: Optional[str] = None,
) -> Container:
    """A compact metric: a bold number over a micro caption.

    The number defaults to the brand colour so the counters read as a bright,
    consistent set; pass ``accent`` to override it for a specific tile.
    """
    number_style = {"color": accent or theme.primary()}
    return Container(
        key=key,
        class_="pd-stat",
        expand=1,
        style=theme.hairline(),
        child=Column(key=f"{key}_col", spacing=2, children=[
            Text(str(value), key=f"{key}_value", class_="pd-stat-num",
                 style=number_style, max_lines=1, overflow="clip"),
            Text(label, key=f"{key}_label", class_="pd-stat-label",
                 max_lines=1, overflow="clip"),
        ]),
    )


# ── Empty / error / loading notices ──────────────────────────────────────────


def spinner(
    size: float = 34,
    *,
    label: str = "",
    color: Optional[str] = None,
    key: str = "pd_spinner",
) -> Column:
    """The one indeterminate spinner every "working…" surface is built from.

    Keeping it here means a connecting card, a scan handshake and a
    recent-app check all spin at the same size and colour.
    """
    children: list[Widget] = [
        CircularProgress(key=f"{key}_ring", size=float(size),
                         color=color or theme.primary()),
    ]
    if label:
        children.append(Text(label, key=f"{key}_label", class_="pd-body",
                             text_align="center"))
    return Column(key=key, spacing=10, horizontal_alignment="center",
                  children=children)


def loading_panel(
    title: str = "Connecting…",
    message: str = "",
    *,
    key: str = "pd_loading",
    tone: str = "info",
) -> Container:
    """A centred spinner with a status line — shown while a link is opening.

    The visual sibling of :func:`notice_state`: same frame, same rhythm, but
    the badge is a live spinner instead of a static glyph.
    """
    accent = {
        "info": theme.info, "success": theme.success,
        "warning": theme.warning, "danger": theme.danger,
    }.get(tone, theme.info)()
    children: list[Widget] = [
        spinner(size=40, color=accent, key=f"{key}_spin"),
        Text(title, key=f"{key}_title", class_="pd-h2", text_align="center"),
    ]
    if message:
        children.append(Text(message, key=f"{key}_msg", class_="pd-body",
                             text_align="center"))
    return Container(
        key=key,
        width="match",
        padding=theme.insets(horizontal=24, vertical=18),
        alignment="center",
        child=Column(key=f"{key}_inner", spacing=12,
                     horizontal_alignment="center", children=children),
    )


def notice_state(
    icon: str,
    title: str,
    message: str = "",
    *,
    key: str = "pd_notice",
    tone: str = "info",
    action: Optional[Widget] = None,
) -> Container:
    """A centred notice with a tinted icon badge — empty, error or loading.

    ``tone`` picks the accent from the status colour system (``info``,
    ``success``, ``warning``, ``danger``), so a failure reads red and an idle
    screen reads neutral without the caller choosing colours.
    """
    accent = {
        "info": theme.info, "success": theme.success,
        "warning": theme.warning, "danger": theme.danger,
    }.get(tone, theme.info)()
    state = _tone_state(tone)
    badge_style = {"bg": theme.status_surface(state)}
    badge_style.update(theme.status_border(state))
    children: list[Widget] = [
        Container(
            key=f"{key}_badge",
            class_="pd-icon-badge",
            style=badge_style,
            child=Text(icon, key=f"{key}_glyph", size=20, color=accent),
        ),
        Text(title, key=f"{key}_title", class_="pd-h2", text_align="center"),
    ]
    if message:
        children.append(Text(message, key=f"{key}_msg", class_="pd-body",
                             text_align="center"))
    if action is not None:
        children.append(action)
    return Container(
        key=key,
        width="match",
        padding=theme.insets(horizontal=24, vertical=18),
        alignment="center",
        child=Column(key=f"{key}_inner", spacing=10,
                     horizontal_alignment="center", children=children),
    )


def _tone_state(tone: str) -> str:
    """Map a notice tone onto a connection state for the shared tint."""
    return {
        "success": "connected", "warning": "connecting",
        "danger": "failed", "info": "syncing",
    }.get(tone, "syncing")


# ── Steps ────────────────────────────────────────────────────────────────────


def step_row(
    index: int,
    title: str,
    text: str,
    *,
    key: str = "pd_step",
) -> Row:
    """One numbered line of the "how it works" explainer."""
    return Row(
        key=key,
        spacing=12,
        main_axis_size="max",
        vertical_alignment="top",
        children=[
            Container(
                key=f"{key}_num",
                class_="pd-step-num",
                style=theme.hairline(theme.primary()),
                child=Text(str(index), key=f"{key}_num_text",
                           class_="pd-step-num-text"),
            ),
            Column(key=f"{key}_body", spacing=2, expand=1, children=[
                Text(title, key=f"{key}_title", class_="pd-meta-val",
                     max_lines=1),
                Text(text, key=f"{key}_text", class_="pd-body"),
            ]),
        ],
    )
