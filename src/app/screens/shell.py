"""The shell — Pydash's root screen with bottom navigation.

Four destinations (Home, Components, Playground, Settings) rendered as one
Scaffold whose body swaps with the selected tab. The bar itself is a fully
configured :class:`~pydrud.BottomNavigationBar`, and the Scaffold's
``adaptive`` flag moves it into a NavigationRail on tablet-width windows —
the framework's own responsive behaviour, not a hand-rolled one.
"""

from __future__ import annotations

from pydrud import (
    AppBar, BottomNavigationBar, InkWell, NavItem, Row, Scaffold, Spacing,
    Text, Theme, Widget,
)

from app.components.identity import Wordmark
from app.components.status import StatusPill
from app.preview.models import ConnectionState
from app.preview.session import session
from app.runtime import refresh, router
from app.state import active_tab, session_pulse

__all__ = ["shell_screen", "TAB_ROUTES"]

#: Destination ids in bar order.
TAB_ROUTES = ("home", "components", "playground", "settings")


def shell_screen(page) -> None:
    """Build the tabbed root screen."""
    from app.screens import components, home, playground, settings

    page.bgcolor = Theme.background

    tab = _clamp_tab(active_tab.value)
    builders = (home.body, components.body, playground.body, settings.body)
    titles = ("Home", "Components", "Playground", "Settings")

    page.add(Scaffold(
        key="pd_shell",
        app_bar=_app_bar(),
        body=_tab_body(tab, builders[tab]),
        bottom_navigation=BottomNavigationBar(
            [
                NavItem("Home", icon="home", route="home"),
                NavItem("Components", icon="apps", route="components"),
                NavItem("Playground", icon="rocket", route="playground"),
                NavItem("Settings", icon="settings", route="settings"),
            ],
            key="pd_shell_nav",
            selected=tab,
            on_change=_select_tab,
            indicator="pill",
            animate=True,
            haptic=False,
        ),
        adaptive=True,
        content_max_width=720,
    ))


def _clamp_tab(value: int) -> int:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(value, len(TAB_ROUTES) - 1))


def _select_tab(event) -> None:
    try:
        active_tab.value = int(event.get("value", active_tab.value))
    except (TypeError, ValueError):
        return
    refresh()


def _app_bar() -> AppBar:
    state = session.state
    return AppBar(
        title=Row(
            key="pd_shell_title",
            spacing=Spacing.SM,
            vertical_alignment="center",
            children=[
                Wordmark("pd_shell_word", size=19,
                         color=Theme.text),
                Text("· Live preview", key="pd_shell_subtitle", size=13,
                     color=Theme.text_secondary),
            ],
        ),
        key="pd_shell_bar",
        actions=[
            StatusPill("pd_shell_status", state).on_click(_open_connection),
        ],
    )


def _open_connection(_event) -> None:
    if session.is_live or session.is_busy:
        router.push("preview")
    else:
        router.push("scan")


def _tab_body(tab: int, builder) -> Widget:
    from app.components import page_body

    return page_body(f"pd_tab_{TAB_ROUTES[tab]}", builder())
