"""Pydash design system.

Builds on Pydrud's :class:`~pydrud.Theme` / :class:`~pydrud.Colors` /
:class:`~pydrud.Tokens` with the small vocabulary every Pydash screen
shares: brand gradients, semantic status colours, monospace metadata
presentation and one helper that keeps the light/dark/system preference
in sync with the running app.

Every helper returns plain serialisable values, so screens stay
declarative and testable.
"""

from __future__ import annotations

from pydrud import Border, Colors, EdgeInsets, Theme, Tokens

from app.config import ACCENT, ACCENT_ALT


def pad(*, all: float = 0, horizontal: float = 0, vertical: float = 0,
        left: float = 0, top: float = 0, right: float = 0,
        bottom: float = 0) -> dict:
    """Serialised padding/margin dict with Flutter-style conveniences.

    ``pad(all=16)``, ``pad(horizontal=20, vertical=8)`` and the explicit
    per-side form all work, mirroring :class:`~pydrud.EdgeInsets`.
    """
    if all:
        return EdgeInsets.all(all).to_dict()
    if horizontal or vertical:
        return EdgeInsets.symmetric(horizontal=horizontal,
                                    vertical=vertical).to_dict()
    return EdgeInsets(left=left, top=top, right=right,
                      bottom=bottom).to_dict()

#: Semantic roles Pydash paints itself with. They resolve against the live
#: theme, so dark mode and user re-seeding keep working everywhere.
def primary() -> str:
    return Theme.primary


def on_primary() -> str:
    return Theme.on_primary


def surface() -> str:
    return Theme.surface


def surface_variant() -> str:
    return Theme.surface_variant


def background() -> str:
    return Theme.background


def text() -> str:
    return Theme.text


def text_secondary() -> str:
    return Theme.text_secondary


def outline() -> str:
    return Theme.outline


def success() -> str:
    return Colors.SUCCESS


def warning() -> str:
    return Colors.WARNING


def error() -> str:
    return Theme.error


def info() -> str:
    return Colors.INFO


#: ── Brand ───────────────────────────────────────────────────────────────────

def brand_gradient(direction: str = "diagonal") -> dict:
    """The signature Pydash gradient style entry."""
    return {
        "gradient": {
            "colors": [ACCENT, Colors.mix(ACCENT, ACCENT_ALT, 0.55)],
            "direction": direction,
        },
    }


def brand_on_surface(opacity: float = 0.9) -> str:
    """Readable white for content painted on the brand gradient."""
    return Colors.with_opacity(Colors.WHITE, opacity)


#: ── Status colour system ────────────────────────────────────────────────────
#: One colour per connection state, used by pills, dots, borders and hero
#: cards so the whole app speaks the same status language.

def status_color(state: str) -> str:
    return {
        "idle": text_secondary(),
        "connecting": warning(),
        "handshaking": warning(),
        "connected": success(),
        "syncing": info(),
        "reconnecting": warning(),
        "failed": error(),
        "disconnected": text_secondary(),
    }.get(state, text_secondary())


def status_surface(state: str) -> str:
    """A translucent tint of the status colour for pill backgrounds."""
    return Colors.with_opacity(status_color(state), 0.14)


#: ── Reusable style fragments ────────────────────────────────────────────────

def hairline() -> dict:
    """The 1dp outline Pydash cards and dividers are drawn with."""
    return {"border": Border(outline(), 1).to_dict()}


def code_style() -> dict:
    """Monospace presentation for URIs, keys and other metadata."""
    return {
        "font": {
            "family": "monospace",
            "size": 12,
            "letterSpacing": 0.02,
        },
    }


def caption_style() -> dict:
    """All-caps micro label used above sections and cards."""
    return {
        "font": {
            "size": 11,
            "weight": 700,
            "letterSpacing": 0.10,
        },
    }


#: ── Theme mode preference ───────────────────────────────────────────────────

def apply_theme_mode(page, mode: str) -> None:
    """Apply a light/dark/system preference to the running app.

    ``page.set_theme_mode`` already handles the native side; this wrapper
    exists so callers have one place to extend (e.g. persisting the
    preference) without every screen repeating the logic.
    """
    page.set_theme_mode(mode)


def seed_brand() -> None:
    """(Re)build the palette from the Pydash brand colour."""
    Theme.seed(ACCENT)


def configure_pydash_tokens() -> None:
    """Nudge the shared design tokens towards Pydash's look.

    Slightly rounder cards and a compact app bar keep the tool feeling
    tight and technical — a preview client should hand the screen to the
    project, not spend it on chrome.
    """
    Tokens.update(
        radius_card=18,
        app_bar_height=44,
    )


__all__ = [
    "apply_theme_mode", "background", "brand_gradient", "brand_on_surface",
    "caption_style", "code_style", "configure_pydash_tokens", "error",
    "hairline", "info", "on_primary", "outline", "primary", "seed_brand",
    "status_color", "status_surface", "success", "surface", "surface_variant",
    "text", "text_secondary", "warning",
]
