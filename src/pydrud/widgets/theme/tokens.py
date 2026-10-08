"""
Design-token scales: spacing, corner radius, elevation and motion.
"""

from __future__ import annotations

from pydrud.widgets.theme._common import _ConstantsMeta

class Spacing(metaclass=_ConstantsMeta):
    """The 4dp spacing scale every Pydrud layout is built on.

    Sticking to a scale is what makes a UI look designed rather than
    assembled::

        Column(spacing=Spacing.MD, children=[...])
        Container(padding=Spacing.LG, child=...)
    """

    NONE = 0
    XXS = 2
    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 24
    XXL = 32
    HUGE = 48

    GUTTER = 20

    @classmethod
    def scale(cls, steps: float) -> int:
        """``Spacing.scale(3)`` → 12dp. Handy for computed gaps."""
        return int(round(steps * 4))

class Radius(metaclass=_ConstantsMeta):
    """Corner radii. Rounded-but-not-bubbly is the modern default."""

    NONE = 0
    XS = 6
    SM = 10
    MD = 14
    LG = 18
    XL = 24
    XXL = 32

    PILL = 999

    CIRCLE = PILL

    FULL = PILL

class Elevation(metaclass=_ConstantsMeta):
    """Shadow depths, named for intent rather than for a number.

    The semantic names survive a design-system change; a raw number does
    not. For code ported from a Material spec the full ``D0``–``D24`` dp
    scale also exists (``Elevation.D4 == 4``).
    """

    FLAT = 0
    HAIRLINE = 1
    CARD = 2
    RAISED = 4
    FLOATING = 6
    DIALOG = 12
    MODAL = 16

    MAX = 24

    @classmethod
    def dp(cls, value: float) -> float:
        """Clamp *value* into the 0–24dp Material elevation range."""
        return max(0.0, min(float(cls.MAX), float(value)))

for _depth in range(Elevation.MAX + 1):
    setattr(Elevation, f"D{_depth}", _depth)
del _depth

class Motion(metaclass=_ConstantsMeta):
    """Durations (ms) and curves — keep animations short and consistent."""

    INSTANT = 80
    FAST = 140
    NORMAL = 220
    SLOW = 320
    LAZY = 480

    STANDARD = "ease_in_out"
    ENTER = "decelerate"
    EXIT = "accelerate"
    SPRING = "overshoot"
    BOUNCE = "bounce"
