"""The Pydash Playground — full-screen, fully interactive framework demos.

Every experience here is real: reactive state, live theming, navigation,
animation, validation, list mutations and gestures, all built from the
current Pydrud SDK. Screens stay in this registry so the Playground index
renders them uniformly and new demos are one entry away.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from pydrud import Widget

__all__ = ["DEMOS", "PlaygroundDemo", "find_demo"]


@dataclass(frozen=True)
class PlaygroundDemo:
    """One playground experience."""

    id: str
    title: str
    blurb: str
    icon: str
    accent: str = ""
    tags: tuple = ()
    #: Builds the demo body; receives the key prefix.
    build: Callable[[str], Widget] = None  # type: ignore[assignment]
    #: Extra routes the demo pushes onto (e.g. detail screens).
    routes: tuple = ()

    @property
    def key(self) -> str:
        return f"pg_{self.id}"


def find_demo(demo_id: str) -> "PlaygroundDemo | None":
    for demo in DEMOS:
        if demo.id == demo_id:
            return demo
    return None


# ── demo modules register themselves below ─────────────────────────────────

from app.data.playground_demos import (  # noqa: E402
    forms, gestures, kitchen, motion, navigation, responsive, state, theme,
    tasks, viz,
)

DEMOS: tuple = (
    state.DEMO,
    theme.DEMO,
    navigation.DEMO,
    motion.DEMO,
    responsive.DEMO,
    forms.DEMO,
    tasks.DEMO,
    gestures.DEMO,
    viz.DEMO,
    kitchen.DEMO,
)
