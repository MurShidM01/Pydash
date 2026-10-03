"""The component showcase catalog.

Every Pydrud UI widget that exists in the current SDK, organised into
categories of *live* demos — nothing here is a screenshot or a mock; each
entry builds the real widget so it behaves exactly as it would in a
shipping app.

A category is a plain dataclass so screens can render it without knowing
where the demos came from, and new widgets join the showcase by adding a
builder — no screen changes required.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from pydrud import Widget

__all__ = ["CATEGORIES", "Category", "Demo", "find_category", "search"]


@dataclass(frozen=True)
class Demo:
    """One live demo inside a category."""

    id: str
    title: str
    description: str = ""
    #: Builds the demo's content; receives the key prefix to use.
    build: Callable[[str], Widget] = None  # type: ignore[assignment]
    tags: tuple = ()

    @property
    def key(self) -> str:
        return f"demo_{self.id}"


@dataclass(frozen=True)
class Category:
    """A group of related widget demos."""

    id: str
    name: str
    icon: str
    blurb: str
    demos: tuple = field(default=())

    @property
    def key(self) -> str:
        return f"cat_{self.id}"

    def find(self, demo_id: str) -> Optional[Demo]:
        for demo in self.demos:
            if demo.id == demo_id:
                return demo
        return None

    def matches(self, query: str) -> bool:
        """Case-insensitive match against name, blurb, demos and tags."""
        text = query.strip().lower()
        if not text:
            return True
        haystack = " ".join(
            [self.name, self.blurb]
            + [demo.title for demo in self.demos]
            + [tag for demo in self.demos for tag in demo.tags]
        ).lower()
        return text in haystack


def find_category(category_id: str) -> Optional[Category]:
    for category in CATEGORIES:
        if category.id == category_id:
            return category
    return None


def search(query: str) -> list:
    """Categories matching *query* (all of them when the query is empty)."""
    return [c for c in CATEGORIES if c.matches(query)]


# ── the catalog itself ──────────────────────────────────────────────────────
# Assembled from focused modules so each widget family stays readable.

from app.data.showcase import (  # noqa: E402
    buttons, chips, inputs, layout, lists, motion, navigation, progress,
    typography, visuals,
)

CATEGORIES: tuple = (
    typography.CATEGORY,
    buttons.CATEGORY,
    inputs.CATEGORY,
    chips.CATEGORY,
    lists.CATEGORY,
    progress.CATEGORY,
    navigation.CATEGORY,
    layout.CATEGORY,
    motion.CATEGORY,
    visuals.CATEGORY,
)
