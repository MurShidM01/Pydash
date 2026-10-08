"""The connect-and-wait flow shared by the scan, home and preview screens.

Every way into a preview — a scanned QR code, a pasted URL, a recent app, a
retry — funnels through :func:`start`. It marks a connection as *pending* (so
the screen that started it can spin instead of showing a stale button), watches
the session, and resolves:

* the link comes up → the preview opens (pushed from Home, replaced from Scan);
* the link fails → the "App is not responding" dialog is raised, with **Go
  Home** and **Retry**;
* a *live* session drops and cannot recover → the same dialog, over the
  preview it was rendering.

Resolution is event-driven: :class:`~app.preview.session.PreviewSession` calls
every :attr:`~app.preview.session.PreviewSession.on_state_hooks` entry on the UI
thread after each state change, so nothing polls.
"""

from __future__ import annotations

from app import state
from app.preview.models import ConnectionState, Endpoint
from app.preview.session import session
from app.runtime import refresh, router

__all__ = [
    "cancel", "failure_dialog", "failure_message", "go_home", "retry", "start",
]

_FAILED_MESSAGE = ("The development server stopped responding. Check that "
                   "`pydrud dev` is still running on your computer.")


# ── starting a connection ────────────────────────────────────────────────────


def start(endpoint: Endpoint, *, origin: str) -> None:
    """Begin a connection the user is waiting on, from *origin*.

    *origin* is ``"scan"`` (opened from the scanner / URL screen) or
    ``"home"`` (a recent app or a reconnect from the dashboard). It decides
    where the preview lands and where a failure is reported.
    """
    state.connection_failed.value = None
    state.connecting.value = True
    state.connecting_endpoint.value = endpoint.as_dict()
    state.connecting_origin.value = origin
    session.connect(endpoint)
    refresh()


def cancel() -> None:
    """Abandon a pending connection (the user tapped Cancel)."""
    _clear()
    session.disconnect(reason="cancelled")
    refresh()


def retry() -> None:
    """Re-attempt the endpoint that just failed."""
    endpoint = session.endpoint
    origin = state.connecting_origin.value or "home"
    state.connection_failed.value = None
    if endpoint is None:
        go_home()
        return
    start(endpoint, origin=origin)


def go_home() -> None:
    """Dismiss the failure and return to the dashboard."""
    _clear()
    state.connection_failed.value = None
    session.disconnect(reason="dismissed")
    try:
        router.reset("shell")
    except Exception:
        pass


# ── the "not responding" dialog ──────────────────────────────────────────────


def failure_message() -> str:
    """The message for the failure dialog, or ``""`` when there is none."""
    pending = state.connection_failed.value
    if pending:
        return str(pending)
    if (session.dropped
            and session.state in (ConnectionState.FAILED,
                                  ConnectionState.DISCONNECTED)
            and router.current_route == "preview"):
        return session.describe_error() or _FAILED_MESSAGE
    return ""


def failure_dialog():
    """The modal shown when the dev server stops responding, or ``None``."""
    message = failure_message()
    if not message:
        return None
    from pydrud import AlertDialog, Icons

    return AlertDialog(
        key="pd_not_responding",
        title="App is not responding",
        message=message,
        icon=Icons.ERROR,
        actions=[("Go Home", "home"), ("Retry", "retry")],
        on_click=_on_dialog_action,
        on_dismiss=lambda _e: _dismiss(),
    )


def _on_dialog_action(event) -> None:
    action = ""
    try:
        action = str(event.data.get("action") or "")
    except Exception:
        action = ""
    _dismiss()
    if action == "retry":
        retry()
    else:
        go_home()


def _dismiss() -> None:
    state.connection_failed.value = None
    session.dropped = False
    refresh()


# ── session → UI resolution ──────────────────────────────────────────────────


def _clear() -> None:
    state.connecting.value = False
    state.connecting_endpoint.value = None
    state.connecting_origin.value = ""


def _on_state(state_name: str) -> None:
    if state.connecting.value:
        if state_name in (ConnectionState.CONNECTED, ConnectionState.SYNCING):
            _finish_live()
        elif state_name in (ConnectionState.FAILED,
                            ConnectionState.DISCONNECTED):
            _finish_failed()
        return
    # A live preview that dropped: raise the dialog over it.
    if (session.dropped
            and state_name in (ConnectionState.FAILED,
                               ConnectionState.DISCONNECTED)
            and router.current_route == "preview"):
        state.connection_failed.value = (
            session.describe_error() or _FAILED_MESSAGE)
        refresh()


def _finish_live() -> None:
    origin = state.connecting_origin.value
    _clear()
    # Adopt the previewed palette *before* the route is built: doing it from
    # inside the builder would nest a render inside the build in progress.
    _adopt_theme()
    if origin == "home":
        router.push("preview")
    else:
        router.replace("preview")


def _adopt_theme() -> None:
    from app.preview.renderer import adopt_remote_theme

    try:
        adopt_remote_theme()
    except Exception:
        pass


def _finish_failed() -> None:
    message = session.describe_error() or _FAILED_MESSAGE
    _clear()
    state.connection_failed.value = message
    refresh()


def _install() -> None:
    if _on_state not in session.on_state_hooks:
        session.on_state_hooks.append(_on_state)


_install()
