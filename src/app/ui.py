"""Backward-compatible imports for the starter's reusable components.

New code should import from :mod:`app.components`. This module remains so
earlier references (and any generated scaffolding) keep working while the
app migrates to the new component package.
"""

from app.components import page_body, section

__all__ = ["page_body", "section"]
