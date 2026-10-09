"""Pydash design system.

Builds on Pydrud's :class:`~pydrud.Theme` / :class:`~pydrud.Colors` /
:class:`~pydrud.Tokens` with the small vocabulary every Pydash screen shares:
semantic roles, status colours, the brand gradient and a few reusable style
fragments. ``app/theme.pss`` refers to the *roles* by token name, so the
stylesheet follows the palette — including the dark one — with no second copy
of every rule.

Every helper returns plain, serialisable values so screens stay declarative and
testable.
"""

from __future__ import annotations

from pydrud import Border, Colors, EdgeInsets, Theme, Tokens

from app.config import (
    ACCENT,
    DANGER,
    DEFAULT_PALETTE,
    INFO,
    PALETTES,
    SUCCESS,
    WARNING,
)

# ── Palette ──────────────────────────────────────────────────────────────────


def palette_seed(name: str | None = None) -> str:
    """The seed colour for a named palette (falls back to the brand accent)."""
    for label, seed in PALETTES:
        if label == (name or DEFAULT_PALETTE):
            return seed
    return ACCENT


def seed_brand(name: str | None = None) -> None:
    """(Re)build the palette from a named accent preset (default: the brand).

    Seeds light **and** dark palettes, so ``page.set_theme_mode`` and the
    framework's system-mode sync keep working without a second palette.
    """
    Theme.seed(palette_seed(name))


def apply_palette(page, name: str) -> None:
    """Re-seed the running app from a named palette and repaint it live."""
    try:
        page.set_theme(palette_seed(name), animate=True)
    except Exception:
        seed_brand(name)
        try:
            from app import state

            apply_theme_mode(page, str(state.theme_mode.value))
        except Exception:
            pass


def configure_tokens() -> None:
    """Nudge the shared design tokens towards Pydash's look.

    Slightly rounder cards and a standard app bar keep the tool feeling tight
    and technical — a preview client hands the screen to the project, so its own
    chrome stays calm.
    """
    Tokens.update(
        radius_card=18,
        radius_button=14,
        radius_input=14,
        radius_sheet=24,
        app_bar_height=56,
        nav_height=64,
        gutter=20,
        section=22,
        card_padding=18,
    )


def is_dark() -> bool:
    """Whether the active palette is the dark one."""
    return bool(getattr(Theme, "dark_mode", False))


# ── Semantic roles (resolve against the live theme) ──────────────────────────


def primary() -> str:
    return Theme.primary


def on_primary() -> str:
    return Theme.on_primary


def background() -> str:
    return Theme.background


def surface() -> str:
    return Theme.surface


def surface_variant() -> str:
    return Theme.surface_variant


def text() -> str:
    return Theme.text


def text_secondary() -> str:
    return Theme.text_secondary


def outline() -> str:
    return Theme.outline


def error() -> str:
    return Theme.error


def success() -> str:
    return SUCCESS


def warning() -> str:
    return WARNING


def info() -> str:
    return INFO


def danger() -> str:
    return DANGER


# ── Brand ────────────────────────────────────────────────────────────────────


def brand_gradient(direction: str = "diagonal") -> dict:
    """The signature Pydash gradient — the primary role into its complement."""
    return {
        "gradient": {
            "colors": [Theme.primary, Colors.mix(Theme.primary, INFO, 0.55)],
            "direction": direction,
        },
    }


def on_brand(opacity: float = 0.92) -> str:
    """Readable near-white for content painted on the brand gradient."""
    return Colors.with_opacity(Colors.WHITE, opacity)


# ── Status colour system ─────────────────────────────────────────────────────
#: One colour per connection state, shared by pills, dots, borders and hero
#: cards so the whole app speaks the same status language.

_STATUS = {
    "idle": danger,
    "connecting": warning,
    "handshaking": warning,
    "connected": success,
    "syncing": info,
    "reconnecting": warning,
    "failed": error,
    "disconnected": danger,
}


def status_color(state: str) -> str:
    entry = _STATUS.get(state)
    return entry() if callable(entry) else (entry or text_secondary())


def status_surface(state: str) -> str:
    """A translucent tint of the status colour for pill/card backgrounds."""
    return Colors.with_opacity(status_color(state), 0.14)


def tint(color: str, opacity: float = 0.14) -> str:
    """A translucent wash of *color* — the background of tinted chips/badges."""
    return Colors.with_opacity(color, opacity)


# ── Reusable style fragments ─────────────────────────────────────────────────


def hairline(color: str | None = None, width: float | None = None) -> dict:
    """The uniform border Pydash cards and tiles are drawn with.

    Defaults to :func:`border_color` / :func:`border_width`, so a card border
    is exactly as strong as an outlined button's.
    """
    return {"border": Border(
        color or border_color(),
        width if width is not None else border_width(),
    ).to_dict()}


def border_color() -> str:
    """The colour every Pydash border is drawn in.

    Matches the outlined-button / outlined-input stroke — the brand colour at
    45% — so borders track the palette (light/dark and any re-seed) instead of
    a fixed grey. Change the theme and every border follows.
    """
    return Colors.with_opacity(primary(), 0.45)


def border_width() -> float:
    """Border width in dp — the same ``border_width``-based stroke as buttons.

    Outlined buttons stroke at ``border_width * 1.4``; borders match so the
    two read as one system.
    """
    return float(Tokens.border_width) * 1.4


def edge_border(*, top: bool = False, bottom: bool = False, left: bool = False,
                right: bool = False, color: str | None = None,
                width: float | None = None) -> dict:
    """A border on selected edges only — e.g. the app bar's bottom rule."""
    return {"border": Border.only(
        color=color or border_color(),
        width=width if width is not None else border_width(),
        top=top, bottom=bottom, left=left, right=right,
    ).to_dict()}


# ── Chrome (app bar / nav bar) rules ─────────────────────────────────────────

#: The chrome rules are deliberately stronger than a card hairline: they are
#: the only thing separating a bar from the content, so a faint line reads as
#: "no line" on a phone. Still fully theme-derived — a deeper brand tint.
CHROME_OPACITY = 0.75
CHROME_WIDTH = 2.0


def chrome_color() -> str:
    """The colour of the app-bar / nav-bar rule (brand colour, deeper)."""
    return Colors.with_opacity(primary(), CHROME_OPACITY)


def chrome_border(*, top: bool = False, bottom: bool = False) -> dict:
    """The edge rule that separates the chrome from the content.

    Same brand hue as :func:`border_color` but at a higher opacity and roughly
    twice the width, so the app bar and nav bar stay clearly defined at any
    display density.
    """
    return edge_border(top=top, bottom=bottom,
                       color=chrome_color(), width=CHROME_WIDTH)


def chrome_outline() -> dict:
    """A *uniform* chrome border around a rounded bar.

    Unlike :func:`chrome_border` (per-side), a uniform border is stroked
    straight onto the rounded shape, so it follows the corners — the bar reads
    as an outlined card instead of a line that stops short at each corner. The
    app bar / nav bar surface is white on a near-white page, so this outline is
    what makes the rounded corners visible at all.
    """
    return {"border": Border(chrome_color(), CHROME_WIDTH).to_dict()}


def chrome_bleed(*, top: bool = False, bottom: bool = False) -> dict:
    """Pull a chrome bar 2dp past the screen edges on the outer sides.

    The outline has to be uniform (a per-side border can't follow a rounded
    corner — it fills the corner instead), so the bar is made slightly larger
    than the screen and shifted outwards: the outer edges and their border hang
    off-screen, and only the inner edge — with its corner arcs — stays visible.
    """
    bleed = -CHROME_WIDTH
    margin = {"left": bleed, "right": bleed}
    if top:
        margin["top"] = bleed
    if bottom:
        margin["bottom"] = bleed
    return {"margin": margin}


def chrome_radius() -> float:
    """Inner-corner radius of the app bar / nav bar — the card radius."""
    return float(Tokens.radius_card)


def rounded_edge(*, top: bool = False, bottom: bool = False,
                 radius: float | None = None) -> dict:
    """Per-corner radii that round *only* the requested edges.

    ``bottom=True`` rounds the two bottom corners (an app bar's inner edge);
    ``top=True`` rounds the two top corners (a bottom bar's inner edge). The
    framework renders these natively through ``GradientDrawable.setCornerRadii``
    and clips the view to the resulting outline, so the corners match a card.
    """
    corner = chrome_radius() if radius is None else float(radius)
    return {
        "borderTopLeftRadius": corner if top else 0,
        "borderTopRightRadius": corner if top else 0,
        "borderBottomLeftRadius": corner if bottom else 0,
        "borderBottomRightRadius": corner if bottom else 0,
    }


def status_border(state: str, width: float = 1) -> dict:
    """A border in the colour of *state* — outlines pills and status badges.

    Pairs with :func:`status_surface`: the tint fills the capsule and this
    outlines it, so a connected pill reads green on both counts and a failed
    one red.
    """
    return {"border": Border(status_color(state), width).to_dict()}


def caption_style() -> dict:
    """All-caps micro label used above sections and cards."""
    return {"font": {"size": 11, "weight": 700, "letterSpacing": 0.10}}


def code_style() -> dict:
    """Monospace presentation for URIs, keys and other metadata."""
    return {"font": {"family": "monospace", "size": 12, "letterSpacing": 0.02}}


def insets(*, all: float = 0, horizontal: float = 0, vertical: float = 0,
           left: float = 0, top: float = 0, right: float = 0,
           bottom: float = 0) -> dict:
    """A serialised padding/margin dict with Flutter-style conveniences."""
    if all:
        return EdgeInsets.all(all).to_dict()
    if horizontal or vertical:
        return EdgeInsets.symmetric(horizontal=horizontal,
                                    vertical=vertical).to_dict()
    return EdgeInsets(left=left, top=top, right=right,
                      bottom=bottom).to_dict()


def page_insets(*, top: float = 0, bottom: float = 0) -> dict:
    """Standard page padding: the live ``gutter`` token on both sides.

    Scrollable screen bodies share one left/right rhythm; passing the vertical
    padding per screen keeps the first and last sections breathing without a
    second class in the stylesheet.
    """
    gutter = float(Tokens.as_dict().get("gutter", 20))
    return EdgeInsets(left=gutter, top=top, right=gutter,
                      bottom=bottom).to_dict()


def apply_theme_mode(page, mode: str) -> None:
    """Apply a light/dark/system preference to the running app."""
    if mode not in ("light", "dark", "system"):
        mode = "system"
    page.set_theme_mode(mode, animate=True)


__all__ = [
    "apply_palette", "apply_theme_mode", "background", "border_color",
    "border_width", "brand_gradient", "caption_style", "chrome_bleed",
    "chrome_border", "chrome_color", "chrome_outline", "chrome_radius",
    "code_style", "configure_tokens", "danger", "edge_border", "error",
    "hairline", "info", "insets", "is_dark", "on_brand", "on_primary",
    "outline", "page_insets", "palette_seed", "primary", "rounded_edge",
    "seed_brand", "status_border", "status_color", "status_surface", "success",
    "surface", "surface_variant", "text", "text_secondary", "tint", "warning",
]
