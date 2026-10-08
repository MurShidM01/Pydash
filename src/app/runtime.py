"""Shared runtime handles: the router, the live App and refresh scheduling.

Screens never import each other; they import this module. It owns:

* :data:`router` — a :class:`~pydrud.Router` subclass that hands the hardware
  back button to a live preview session first;
* :func:`refresh` — rebuild the current screen;
* :func:`on_ui` — marshal work onto the app's single UI thread (the preview
  socket reader thread must never touch widgets directly).
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from pydrud import App, Router

#: The app's router. Screens are registered in ``app.main``.
router: "PydashRouter"


class PydashRouter(Router):
    """The Pydrud router with two preview-aware extensions.

    * While a live preview session is active on the preview route, the hardware
      back button is offered to the *remote* project first — the previewed app
      pops its own navigation stack. Only when the remote declines does the
      local router pop, taking the user back to the Pydash dashboard.
    * Connect deep links are intercepted before the generic URL router. The
      connection URL carries a ``name`` query parameter (the project name),
      which would collide with ``Router.push(name=...)``; Pydash therefore
      parses those links itself through :attr:`link_handler`.
    """

    def __init__(self) -> None:
        super().__init__()
        #: Set by the preview screen while it is the active route; returns True
        #: when the remote project accepted the back press.
        self.preview_back_handler: Optional[Callable[[], bool]] = None
        #: Given a URL, returns True when it was handled here. Registered in
        #: ``app.main`` for preview connect links.
        self.link_handler: Optional[Callable[[str], bool]] = None

    def handle_back(self) -> bool:
        handler = self.preview_back_handler
        if handler is not None and self.current_route == "preview":
            try:
                if handler():
                    # The remote project consumed the press (it answers with a
                    # ``back_result`` and pops the local stack itself when its
                    # own stack is at the root).
                    return True
            except Exception:
                pass
        return super().handle_back()

    def handle_link(self, url: str) -> bool:
        handler = self.link_handler
        if handler is not None:
            try:
                if handler(url):
                    return True
            except Exception:
                pass
        return super().handle_link(url)


router = PydashRouter()

_app: Optional[App] = None


def bind(instance: App) -> App:
    """Remember the running :class:`~pydrud.App` and return it."""
    global _app
    _app = instance
    return instance


def current() -> Optional[App]:
    """The running app, falling back to the most recently created one."""
    return _app if _app is not None else App.current()


def refresh() -> None:
    """Re-render the current screen."""
    app = current()
    if app is not None:
        app.update()


def on_ui(fn: Callable, *args: Any, **kwargs: Any) -> None:
    """Run *fn* on the app's UI thread (no-op fallback before startup).

    Background threads (the preview socket reader, reconnect timers) must route
    every widget-visible mutation through here.

    The UI queue is bounded. When it is saturated — a preview applying render
    transactions faster than the UI can draw — the framework's ``run_on_ui``
    raises rather than block, and that exception used to escape into the
    *calling* worker thread and kill the preview's reader. Swallow it instead:
    a dropped rebuild is harmless because rebuilds are coalesced, so the next
    transaction re-schedules one.
    """
    app = current()
    if app is None:
        try:
            fn(*args, **kwargs)
        except Exception:
            pass
        return
    try:
        app.run_on_ui(fn, *args, **kwargs)
    except Exception:
        pass


def after(delay: float, fn: Callable, *args: Any, **kwargs: Any):
    """Schedule *fn* on the app's task runner after *delay* seconds."""
    app = current()
    if app is None:
        return None
    return app.tasks.after(delay, fn, *args, **kwargs)


__all__ = ["PydashRouter", "after", "bind", "current", "on_ui", "refresh",
           "router"]
