"""Reusable Pydash UI components.

Four small modules, one flat import surface:

* :mod:`app.components.common` — app bars, surfaces, spinners, headers,
  metadata, stats, notices and the "how it works" steps
* :mod:`app.components.brand`  — the gradient brand hero
* :mod:`app.components.status` — connection-state dot and pill
"""

from app.components.brand import brand_hero
from app.components.common import (
    APP_BAR_HEIGHT,
    app_bar,
    bar_action,
    card,
    loading_panel,
    meta_list,
    notice_state,
    section_header,
    spinner,
    stat_tile,
    step_row,
)
from app.components.status import status_dot, status_pill

__all__ = [
    "APP_BAR_HEIGHT", "app_bar", "bar_action", "brand_hero", "card",
    "loading_panel", "meta_list", "notice_state", "section_header", "spinner",
    "stat_tile", "status_dot", "status_pill", "step_row",
]
