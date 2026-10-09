"""The shell — the app bar and bottom navigation over Home and Settings.

One professional chrome around the two destinations the user lives in:

* a calm app bar that shows the Pydash wordmark on Home and a plain title on
  Settings, with a one-tap route to the scanner;
* a Material bottom navigation bar that swaps the body without touching the
  router — the tab lives in :data:`app.state.active_tab`, so a rebuild is all
  it takes and the preview route can sit on top of the shell untouched.

Screens are imported lazily inside :func:`_tab_body` so the three screen
modules never import each other at module scope.
"""

from __future__ import annotations

from pydrud import (
    BottomNavigationBar,
    Container,
    Icon,
    Icons,
    NavItem,
    Scaffold,
    Text,
)

from app import connection, prefs, recents, state, theme
from app.components import app_bar, bar_action
from app.config import APP_NAME
from app.runtime import refresh, router

__all__ = ["shell_screen"]

_TABS = (0, 1)


def shell_screen(page) -> None:
    """Route builder: the Home / Settings shell."""
    prefs.load(page)
    recents.load(page)
    tab = _tab()
    page.add(Scaffold(
        key="pd_shell",
        class_="pd-screen",
        bg_color=theme.background(),
        app_bar=_app_bar(tab),
        body=_tab_body(tab),
        bottom_navigation=_navigation(tab),
    ))
    dialog = connection.failure_dialog()
    if dialog is not None:
        page.add_floating(dialog)


# ── chrome ───────────────────────────────────────────────────────────────────


def _app_bar(tab: int):
    if tab == 1:
        return app_bar(
            "Settings",
            leading=Icon(Icons.SETTINGS, key="pd_bar_mark", size=22,
                         color=theme.primary()),
            key="pd_bar",
        )
    return app_bar(
        Text(APP_NAME, key="pd_bar_title", class_="pd-h2"),
        leading=Icon(Icons.PYTHON, key="pd_bar_mark", size=22,
                     color=theme.primary()),
        actions=[bar_action(
            Icons.QR_CODE, "Scan QR code",
            lambda: router.push("scan", mode="scan"),
            key="pd_bar_scan",
        )],
        key="pd_bar",
    )


def _navigation(tab: int) -> Container:
    """The bottom navigation, dressed as a card along its top edge.

    Pydrud's nav bar paints a *uniform* corner radius, so the bar itself is
    drawn transparent and a container behind it supplies the surface with only
    the two top corners rounded and a chrome outline stroked onto that shape.
    The outline is uniform, so the surface bleeds 2dp off the sides and bottom
    — that hides the outer edges and leaves the rule on the top edge alone.
    """
    return Container(
        key="pd_nav_surface",
        width="match",
        style={"bg": theme.surface(), **theme.chrome_outline(),
               **theme.rounded_edge(top=True), **theme.chrome_bleed(bottom=True)},
        child=BottomNavigationBar(
            key="pd_nav",
            items=[
                NavItem("Home", icon=Icons.HOME, active_icon=Icons.HOME),
                NavItem("Settings", icon=Icons.SETTINGS,
                        active_icon=Icons.SETTINGS),
            ],
            selected=tab,
            on_change=_on_tab_change,
            # The Material 3 pill behind the active tab reads as a shadowy
            # rectangle; the coloured icon + label already mark the selection,
            # so drop the pill and keep everything else.
            indicator="none",
            haptic=True,
            # The wrapper draws the surface (and the safe-area inset), so the
            # bar paints nothing and keeps to its content height.
            bg="#00000000",
            safe_area=False,
        ),
    )


# ── behaviour ────────────────────────────────────────────────────────────────


def _tab() -> int:
    try:
        value = int(state.active_tab.value)
    except (TypeError, ValueError):
        value = 0
    return value if value in _TABS else 0


def _tab_body(tab: int):
    if tab == 1:
        from app.screens.settings import body as settings_body

        return settings_body()
    from app.screens.home import body as home_body

    return home_body()


def _on_tab_change(event) -> None:
    try:
        index = int(event.value)
    except (TypeError, ValueError):
        index = 0
    index = index if index in _TABS else 0
    # The native bar re-reports the selection when the patch that set it is
    # applied, so a tap can arrive twice. Rebuilding for a tab that is already
    # showing is pure work — the screen is identical — so drop it.
    if index == _tab():
        return
    state.active_tab.value = index
    refresh()
