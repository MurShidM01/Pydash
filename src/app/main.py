"""Pydash — entry point.

Registers the shell, scanner and preview routes, applies the design system and
wires deep links so ``pydash://preview/connect?...`` opens straight into a
session.

The generated ``app.android_main`` imports this module for the theme and the
route table, then boots the :class:`~pydrud.App` itself. :func:`start_app`
below is the equivalent entry point for desktop runs and tests.
"""

from __future__ import annotations

import os
import urllib.parse
from typing import Optional

from pydrud import App

from app import theme
from app.config import APP_NAME
from app.preview.models import Endpoint
from app.preview.session import session
from app.preview.uri import PreviewUriError, normalise_uri, parse_preview_uri
from app.runtime import bind, refresh, router
from app.screens.preview import preview_screen
from app.screens.scan import scan_screen
from app.screens.shell import shell_screen

# ── design system ────────────────────────────────────────────────────────────
# Seeding at import time means the palette is ready before the first frame —
# the generated ``app.android_main`` relies on that.

theme.seed_brand()
theme.configure_tokens()

# ── routes ───────────────────────────────────────────────────────────────────

router.define("shell", shell_screen)
router.define("scan", scan_screen)
router.define("preview", preview_screen)
router.initial("shell")


def main(page) -> None:
    """Build the current screen (called on startup and on every update)."""
    router.build_root()(page)


# ── deep links ───────────────────────────────────────────────────────────────
#
# A connect link carries a ``name`` query parameter (the project name), which
# would collide with ``Router.push(name=...)`` in the generic URL router, so
# Pydash intercepts connect links itself (see ``PydashRouter.handle_link``).


def _handle_connect_link(url: str) -> bool:
    """Start a session from a connect deep link.

    Returns ``True`` when *url* was a preview connect link (handled here) and
    ``False`` so the router can try its own URL matching.
    """
    params = _connect_params(url)
    if params is None:
        return False
    endpoint = _endpoint_from_params(params)
    if endpoint is None:
        router.replace("shell")
        return True
    session.connect(endpoint)
    # Adopt any cached palette before the route builds; a first-time theme
    # push arrives after the handshake and is applied by the renderer then.
    from app.preview.renderer import adopt_remote_theme

    try:
        adopt_remote_theme()
    except Exception:
        pass
    router.replace("preview")
    return True


def _connect_params(url: str) -> Optional[dict]:
    """The query parameters of a connect link, or ``None`` when it is not one."""
    parts = urllib.parse.urlsplit(str(url))
    authority = parts.netloc.lower()
    path = parts.path.rstrip("/").lower()
    is_connect = (
        (authority == "preview" and path == "/connect")
        or authority == "connect"
        or path == "/connect"
    )
    if not is_connect:
        return None
    query = urllib.parse.parse_qs(parts.query)
    return {key: values[0] for key, values in query.items() if values}


def _endpoint_from_params(params: dict) -> Optional[Endpoint]:
    """Build an endpoint from connect params, or ``None`` when unusable."""
    uri = params.get("uri")
    if uri:
        try:
            target = parse_preview_uri(normalise_uri(str(uri)))
        except PreviewUriError:
            return None
        return Endpoint(
            host=target.host, port=target.port,
            session_id=target.session_id, token=target.token,
            project_id=target.project_id, project_name=target.project_name,
        )
    try:
        host = str(params["host"]).strip()
        port = int(params["port"])
        session_id = str(params["session"])
        token = str(params["token"])
    except (KeyError, TypeError, ValueError):
        return None
    if not host or not session_id or not token or not 1 <= port <= 65535:
        return None
    return Endpoint(
        host=host, port=port, session_id=session_id, token=token,
        project_id=str(params.get("project", "")),
        project_name=str(params.get("name", "")),
    )


router.link_handler = _handle_connect_link


# ── startup ──────────────────────────────────────────────────────────────────


def start_app() -> None:
    """Local entry point: desktop ``pydrud run`` and tests.

    On device the generated ``app.android_main`` performs the same wiring and
    boots the app itself; this keeps a desktop run identical.
    """
    app = bind(App(
        target=router.build_root(),
        title=APP_NAME,
        stylesheet=os.path.join(os.path.dirname(__file__), "theme.pss"),
    ))
    app.attach_router(router)
    # Deep links are delivered to ``router.handle_link`` automatically once a
    # router is attached; ``PydashRouter`` forwards connect links to
    # ``_handle_connect_link`` above.
    app.run()


__all__ = ["main", "refresh", "router", "start_app"]
