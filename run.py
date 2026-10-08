#!/usr/bin/env python3
"""Local runner for Pydash.

* ``python run.py``         build the widget tree on this machine (headless).
* ``python run.py --tree``  print the full widget tree as JSON.
* ``python run.py --tab N`` build a specific shell tab body (0 Home, 1 Settings).

The on-device app boots through the generated ``app.android_main`` entry point;
this helper is for quick, device-free checks while developing.
"""

import os
import sys

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(PROJECT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


def _build_page():
    from pydrud import Column

    from app.main import main

    page = Column(key="root", spacing=0)
    main(page)
    return page


def main() -> int:
    if "--tree" in sys.argv:
        print(_build_page().to_json())
        return 0

    if "--tab" in sys.argv:
        index = 0
        try:
            index = int(sys.argv[sys.argv.index("--tab") + 1])
        except (IndexError, ValueError):
            index = 0
        from app import state
        from app.screens import home, settings

        state.active_tab.value = index
        body = home.body() if index == 0 else settings.body()
        print(body.to_json())
        return 0

    page = _build_page()
    print(f"built {len(page.children)} root node(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
