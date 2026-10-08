"""Screens.

* :mod:`app.screens.shell`    — the Home / Settings chrome (root route)
* :mod:`app.screens.home`     — the dashboard (a tab body)
* :mod:`app.screens.settings` — preferences and app info (a tab body)
* :mod:`app.screens.scan`     — QR camera / manual URL entry (pushed route)
* :mod:`app.screens.preview`  — the immersive live render (pushed route)
"""

from app.screens.home import body as home_body
from app.screens.preview import preview_screen
from app.screens.scan import scan_screen
from app.screens.settings import body as settings_body
from app.screens.shell import shell_screen

__all__ = [
    "home_body", "preview_screen", "scan_screen", "settings_body",
    "shell_screen",
]
