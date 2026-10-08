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

from app.config import ACCENT, DANGER, INFO, SUCCESS, WARNING

# ── Palette ──────────────────────────────────────────────────────────────────


def seed_brand() -> None:
    """(Re)build the palette from the Pydash brand colour.

    Seeds light **and** dark palettes, so ``page.set_theme_mode`` and the
    framework's system-mode sync keep working without a second palette.
    """
    Theme.seed(ACCENT)


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
    "idle": lambda: text_secondary(),
    "connecting": warning,
    "handshaking": warning,
    "connected": success,
    "syncing": info,
    "reconnecting": warning,
    "failed": error,
    "disconnected": lambda: text_secondary(),
}


def status_color(state: str) -> str:
    entry = _STATUS.get(state)
    return entry() if callable(entry) else (entry or text_secondary())


def status_surface(state: str) -> str:
    """A translucent tint of the status colour for pill/card backgrounds."""
    return Colors.with_opacity(status_color(state), 0.14)


# ── Reusable style fragments ─────────────────────────────────────────────────


def hairline(color: str | None = None) -> dict:
    """The 1dp outline Pydash cards and dividers are drawn with."""
    return {"border": Border(color or outline(), 1).to_dict()}


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
    "apply_theme_mode", "background", "brand_gradient", "caption_style",
    "code_style", "configure_tokens", "danger", "error", "hairline", "info",
    "insets", "is_dark", "on_brand", "on_primary", "outline", "page_insets",
    "primary", "seed_brand", "status_color", "status_surface", "success",
    "surface", "surface_variant", "text", "text_secondary", "warning",
]
