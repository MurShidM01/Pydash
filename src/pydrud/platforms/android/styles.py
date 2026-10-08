"""Renderer-profile data for the generated standalone client.

The shared stylesheet engine consumes only :class:`RendererProfile` data;
Android-specific rendering facts stay in this adapter module.
"""

from __future__ import annotations

from pydrud.core.styles.schema import VALID_STYLE_KEYS
from pydrud.core.styles.resolver import RendererProfile

class AndroidRendererProfile(RendererProfile):
    """Verified style and widget behavior of Pydrud's Android renderer."""

    def __init__(self) -> None:
        super().__init__(

            background_owners=(
                "Button", "TextField", "Checkbox", "Switch", "Radio",
                "Slider", "RangeSlider", "Dropdown",
            ),
            conflict_pairs=(("textAlign", "alignment"),),
            style_keys=VALID_STYLE_KEYS,

            widget_types=None,
        )

__all__ = ["AndroidRendererProfile"]
