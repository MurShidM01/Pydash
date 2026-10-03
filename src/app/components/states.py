"""Polished loading / empty / error surfaces.

Every screen's "nothing to show yet" moment goes through here so the app
keeps one consistent voice: an icon in a soft tinted circle, a title, a
helpful line, and (when useful) one clear action.
"""

from __future__ import annotations

from typing import Callable, Optional

from pydrud import (
    Colors, Column, Container, Icon, Radius, Row, Spacing, Text, Theme,
    Widget,
)

from app.theme import status_color

__all__ = ["NoticeState", "LoadingSurface", "EmptySurface", "ErrorSurface"]


def _tinted_icon(key: str, icon: str, color: str) -> Widget:
    return Container(
        key=f"{key}_ring",
        width=64,
        height=64,
        border_radius=Radius.PILL,
        bg=_tint(color),
        alignment="center",
        child=Icon(icon, key=f"{key}_glyph", size=30, color=color),
    )


def _tint(color: str) -> str:
    return Colors.with_opacity(color, 0.12)


def NoticeState(
    key: str,
    *,
    icon: str,
    title: str,
    message: str,
    tone: str = "idle",
    action: Optional[str] = None,
    on_action: Optional[Callable] = None,
    progress: bool = False,
) -> Widget:
    """A centred notice: icon, title, message, optional action."""
    color = {
        "idle": Colors.PRIMARY, "pending": Colors.WARNING,
        "error": Colors.ERROR, "success": Colors.SUCCESS,
        "info": Colors.INFO,
    }.get(tone, Colors.PRIMARY)

    children: list[Widget] = [_tinted_icon(key, icon, color)]
    if progress:
        from pydrud import CircularProgress

        children.append(Container(key=f"{key}_spin_slot", height=Spacing.LG,
                                  alignment="center",
                                  child=CircularProgress(
                                      key=f"{key}_spin", size=28, stroke=3,
                                      color=color)))
    children.extend([
        Text(title, key=f"{key}_title", size=17, weight=700,
             color=Theme.text, text_align="center"),
        Text(message, key=f"{key}_message", size=13,
             color=Theme.text_secondary,
             text_align="center"),
    ])
    if action and on_action is not None:
        children.append(Container(key=f"{key}_action_gap",
                                  height=Spacing.XS))
        children.append(_action_button(key, action, on_action, color))
    return Column(
        key=key,
        spacing=Spacing.SM,
        horizontal_alignment="center",
        vertical_alignment="center",
        expand=1,
        children=children,
    )


def _action_button(key: str, label: str, on_click: Callable,
                   color: str) -> Widget:
    from pydrud import Button

    return Button(label, key=f"{key}_action", variant="tonal",
                  on_click=on_click, color=color)


def LoadingSurface(key: str, label: str = "Loading…") -> Widget:
    """Centred spinner with a quiet label."""
    from pydrud import CircularProgress

    return Column(
        key=key,
        spacing=Spacing.MD,
        horizontal_alignment="center",
        vertical_alignment="center",
        expand=1,
        children=[
            CircularProgress(key=f"{key}_spin", size=30, stroke=3),
            Text(label, key=f"{key}_label", size=13,
                 color=Theme.text_secondary),
        ],
    )


def EmptySurface(
    key: str,
    *,
    icon: str,
    title: str,
    message: str,
    action: Optional[str] = None,
    on_action: Optional[Callable] = None,
) -> Widget:
    """Nothing here (yet) — with guidance instead of a blank hole."""
    return NoticeState(key, icon=icon, title=title, message=message,
                       tone="idle", action=action, on_action=on_action)


def ErrorSurface(
    key: str,
    *,
    title: str,
    message: str,
    retry: Optional[str] = "Try again",
    on_retry: Optional[Callable] = None,
) -> Widget:
    """Something broke — say what, and offer the way out."""
    return NoticeState(key, icon="error", title=title, message=message,
                       tone="error", action=retry, on_action=on_retry)
