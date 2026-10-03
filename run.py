#!/usr/bin/env python3
"""Development runner for Pydash.

Runs the app's Python side on your computer. Without an Android device
listening on the bridge port it starts in headless mode, which is useful
for checking that the widget tree builds and for unit-testing screens::

    python run.py            # headless (prints the widget tree summary)
    python run.py --tree     # dump the full widget tree as JSON

The tree built here is the real shell — Home dashboard, tab bar, catalog
and playground registries included — so a successful build means every
screen and demo in the app is constructible against the vendored SDK.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from app.main import create_app  # noqa: E402


def main() -> int:
    app = create_app()

    if "--tree" in sys.argv:
        print(app.build().to_json())
        return 0

    tree = app.build()
    widgets = sum(1 for _ in tree.walk())
    print(f"[Pydash] Widget tree built: {widgets} widgets")

    session_tab = "--tab" in sys.argv
    if session_tab:
        # Just verify every tab body constructs, then exit.
        from app.screens import components, home, playground, settings

        for name, builder in (("home", home.body),
                              ("components", components.body),
                              ("playground", playground.body),
                              ("settings", settings.body)):
            count = sum(1 for widget in builder() for _ in widget.walk())
            print(f"[Pydash]   {name:<12} {count:>4} widgets")
        return 0

    app.run(max_retries=3)
    return 0


if __name__ == "__main__":
    sys.exit(main())
