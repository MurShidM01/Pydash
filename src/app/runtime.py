"""Shared runtime handles: the router, the live App and refresh scheduling.

Screens never import each other; they import this module. It owns:

* :data:`router` — a :class:`~pydrud.Router` subclass that knows how to
  hand the hardware back button to a live preview session first;
* :func:`refresh` — rebuild the current screen;
* :func:`on_ui` — marshal work onto the app's single UI thread (socket
  reader threads must never touch widgets directly).
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from pydrud import App, Router

#: The app's router. Screens are registered in ``app.main``.
router: "PydashRouter"


class PydashRouter(Router):
    """The Pydrud router with one preview-aware extension.

    While a live preview session is active on the current route, the
    hardware back button is offered to the *remote* project first — the
    previewed app pops its own navigation stack. Only when the remote
    declines (its stack is at the root) does the local router pop, taking
    the user back to the Pydash dashboard.
    """

    def __init__(self) -> None:
        super().__init__()
        #: Set by the preview screen while it is the active route.
        self.preview_back_handler: Optional[Callable[[], bool]] = None

    def handle_back(self) -> bool:
        handler = self.preview_back_handler
        if (handler is not None and self.current_route == "preview"
                and self._stack.can_pop()):
            # The remote app gets the first chance; it answers asynchronously
            # (a ``back_result`` command) and pops the local stack itself
            # when the remote has nothing to go back to.
            try:
                handler()
            except Exception:
                return self.pop()
            return True
        return super().handle_back()


router = PydashRouter()

_app: Optional[App] = None


def bind(instance: App) -> App:
    """Remember the running :class:`~pydrud.App` and return it."""
    global _app
    _app = instance
    return instance


def current() -> Optional[App]:
    """The running app.

    Falls back to the most recently created :class:`~pydrud.App`, so tests
    and the dev runner work without calling :func:`bind` first.
    """
    return _app if _app is not None else App.current()


def refresh() -> None:
    """Re-render the current screen."""
    app = current()
    if app is not None:
        app.update()


def on_ui(fn: Callable, *args: Any, **kwargs: Any) -> None:
    """Run *fn* on the app's UI thread (no-op fallback before startup).

    Background threads (the preview socket reader, reconnect timers) must
    route every widget-visible mutation through here.
    """
    app = current()
    if app is None:
        try:
            fn(*args, **kwargs)
        except Exception:
            pass
        return
    app.run_on_ui(fn, *args, **kwargs)


def after(delay: float, fn: Callable, *args: Any, **kwargs: Any):
    """Schedule *fn* on the app's task runner after *delay* seconds."""
    app = current()
    if app is None:
        return None
    return app.tasks.after(delay, fn, *args, **kwargs)


__all__ = ["PydashRouter", "after", "bind", "current", "on_ui", "refresh",
           "router"]
