"""Pydash — application entry point and route table.

The route map:

============  ============================================  ===========================
Route         Screen                                        Notes
============  ============================================  ===========================
``shell``     Tabbed root (Home · Components · Playground)  Settings is the 4th tab
``scan``      QR scanner + manual entry                     pushed over the shell
``preview``   Live preview host                             the remote project renders
``category``  Component category detail                     ``?cat=<id>``
``demo``      Playground demo                               ``?id=<id>``
============  ============================================  ===========================

Deep links work with both the app's own ``pydash://`` scheme and the
``pydrud://preview/connect?…`` URI printed by ``pydrud dev``: the route
``/preview/connect`` receives the QR payload's query parameters, validates
them and starts the session straight away.
"""

from __future__ import annotations

from pydrud import App, Column, Theme

from app.config import ACCENT, APP_NAME
from app.preview.renderer import handle_metrics
from app.runtime import bind, refresh, router
from app.screens import components, playground, scan, shell
from app.screens.preview import preview_screen
from app.theme import configure_pydash_tokens, seed_brand

__all__ = ["create_app", "main", "start_app"]


# ── routes ──────────────────────────────────────────────────────────────────

def _register_routes() -> None:
    router.define("shell", shell.shell_screen)
    router.define("scan", scan.scan_screen, transition="slide_up")
    router.define("preview", preview_screen, transition="fade")
    router.define("category", components.category_screen,
                  transition="slide_left")
    router.define("demo", playground.demo_screen, transition="slide_left")

    # The playground's pushed item screen (parameters + transitions demo).
    from app.data.playground_demos.navigation import item_screen

    router.define("playground/item", item_screen, transition="slide_left")

    # Deep link from the `pydrud dev` QR code:
    #   pydrud://preview/connect?host=…&port=…&session=…&token=…
    router.define("/preview/connect", _deep_link_connect)
    router.not_found(_not_found_screen)

    router.initial("shell")


def _deep_link_connect(page, params=None) -> None:
    """A QR payload opened from outside the app (any scanner)."""
    from urllib.parse import urlencode

    from app.preview.models import Endpoint
    from app.preview.session import session
    from app.preview.uri import PreviewUriError, parse_preview_uri

    params = dict(params or {})
    uri = "pydrud://preview/connect?" + urlencode(
        {k: str(v) for k, v in params.items() if v})
    try:
        target = parse_preview_uri(uri)
    except PreviewUriError:
        # Unusable payload — land in manual entry with the URI prefilled.
        scan.scan_screen(page, {"mode": "manual", "uri": uri})
        return
    session.connect(Endpoint(
        host=target.host, port=target.port,
        session_id=target.session_id, token=target.token,
        project_id=target.project_id,
        project_name=target.project_name))
    preview_screen(page)


def _not_found_screen(page, params=None) -> None:
    """Friendly 404 for unknown deep links."""
    params = dict(params or {})
    page.bgcolor = Theme.background
    page.add(Column(key="pd_404", spacing=8, children=[
        Column(key="pd_404_inner", spacing=8, children=[
            Text404("Nothing here"),
            Text404(f"No route matches {params.get('path', 'that link')}.",
                    secondary=True),
        ]),
    ]))


def Text404(value: str, secondary: bool = False):
    from pydrud import Text

    return Text(value, key=f"pd_404_t{int(secondary)}",
                size=18 if not secondary else 13,
                weight=700 if not secondary else 400,
                color=Theme.text if not secondary else Theme.text_secondary)


# ── the root target ─────────────────────────────────────────────────────────

def main(page) -> None:
    """The App target: render the current route's screen."""
    router.build_root()(page)


# ── lifecycle hooks ─────────────────────────────────────────────────────────

def _on_metrics_change(_info=None) -> None:
    """Rotation, split screen, foldables: tell the dev server, reflow."""
    handle_metrics()
    refresh()


def _on_error(_exc) -> None:
    from app.preview.session import session

    session.error = "A screen raised an error while rendering."
    session.error_code = "app"
    refresh()


# ── bootstrap ───────────────────────────────────────────────────────────────

def create_app(**kwargs) -> App:
    """Build the Pydrud App with routes and hooks wired up."""
    seed_brand()
    configure_pydash_tokens()
    _register_routes()

    app = App(target=main, title=APP_NAME, **kwargs)
    bind(app)
    app.attach_router(router)
    app.on_deep_link(_on_deep_link)

    app.on_metrics_change(_on_metrics_change)
    app.on_error(_on_error)
    return app


def _on_deep_link(url: str) -> None:
    """Log arriving links; routing itself is handled by the Router."""
    print(f"[{APP_NAME}] deep link: {url}")


def start_app() -> None:
    """Entry point invoked by the generated Android activity."""
    create_app().run()
