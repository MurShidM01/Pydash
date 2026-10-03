"""The shell — Pydash's root screen with bottom navigation.

Two destinations (Home, Settings) rendered as one Scaffold whose body swaps
with the selected tab. The bar itself is a fully configured
:class:`~pydrud.BottomNavigationBar`, and the Scaffold's ``adaptive`` flag
moves it into a NavigationRail on tablet-width windows — the framework's
own responsive behaviour, not a hand-rolled one.

Pydash is a preview client first: the shell stays out of the way so the
Home dashboard (and whatever project it is previewing) owns the screen.
"""

from __future__ import annotations

from pydrud import (
    AppBar, BottomNavigationBar, Colors, Container, EdgeInsets, NavItem,
    Radius, Row, Scaffold, Spacer, Spacing, Text, Theme, Widget,
)

from app.components.identity import Wordmark
from app.preview.models import ConnectionState
from app.preview.session import session
from app.runtime import refresh, router
from app.state import active_tab

__all__ = ["shell_screen", "TAB_ROUTES"]

#: Destination ids in bar order.
TAB_ROUTES = ("home", "settings")


def shell_screen(page) -> None:
    """Build the tabbed root screen."""
    from app.screens import home, settings

    page.bgcolor = Theme.background

    tab = _clamp_tab(active_tab.value)
    builders = (home.body, settings.body)

    page.add(Scaffold(
        key="pd_shell",
        app_bar=_app_bar(),
        body=_tab_body(tab, builders[tab]),
        bottom_navigation=BottomNavigationBar(
            [
                NavItem("Home", icon="home", route="home"),
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
    """A standard compact header: wordmark, tagline, and connection status dot."""
    is_connected = session.is_live or session.state == ConnectionState.CONNECTED
    dot_color = Colors.SUCCESS if is_connected else Colors.ERROR

    return AppBar(
        title=Row(
            key="pd_shell_title",
            spacing=Spacing.SM,
            vertical_alignment="center",
            children=[
                Wordmark("pd_shell_word", size=18,
                         color=Theme.text),
                Text("· Live preview", key="pd_shell_subtitle", size=12,
                     color=Theme.text_secondary),
                Spacer(key="pd_shell_gap"),
                Container(
                    key="pd_shell_status",
                    padding=EdgeInsets.all(8),
                    alignment="center",
                    child=Container(
                        key="pd_shell_status_dot",
                        width=10,
                        height=10,
                        border_radius=Radius.PILL,
                        bg=dot_color,
                    ),
                ).on_click(_open_connection),
            ],
        ),
        key="pd_shell_bar",
        padding=EdgeInsets(left=16, top=8, right=16, bottom=8),
    )


def _open_connection(_event) -> None:
    if session.is_live or session.is_busy:
        router.push("preview")
    else:
        router.push("scan")


def _tab_body(tab: int, builder) -> Widget:
    from app.components import page_body

    return page_body(f"pd_tab_{TAB_ROUTES[tab]}", builder())
