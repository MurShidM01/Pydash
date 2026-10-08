"""The preview session manager — Pydash's connection state machine.

One module-level :data:`session` instance owns the whole preview lifecycle:

* :meth:`connect` from a scanned/entered endpoint — handshake, first snapshot,
  live updates;
* auto-reconnect with capped backoff when the link drops unexpectedly;
* :meth:`disconnect` — clean shutdown that restores Pydash's own theme;
* statistics (revision, snapshots, patches, events, last sync) surfaced by the
  Home dashboard and the preview header.

State changes are published through the reactive ``State`` objects in
:mod:`app.state`, and every UI-visible mutation is marshalled onto the app's
UI thread via :func:`app.runtime.on_ui`.
"""

from __future__ import annotations

import threading
from typing import Optional

from pydrud.core.responsive import MediaQuery

from app.config import (
    RECONNECT_BASE_DELAY,
    RECONNECT_MAX_ATTEMPTS,
    RECONNECT_MAX_DELAY,
)
from app.preview.client import PreviewClient, PreviewHandshakeError
from app.preview.mirror import RemoteTree
from app.preview.models import (
    ConnectionState,
    Endpoint,
    ServerInfo,
    SessionStats,
)
from app.runtime import after, on_ui, refresh
from app.state import auto_reconnect, bump, haptics_enabled, last_endpoint

__all__ = ["PreviewSession", "session"]


class PreviewSession:
    """Tracks one live-preview relationship with a development server."""

    def __init__(self):
        self.tree = RemoteTree()
        self.endpoint: Optional[Endpoint] = None
        self.client: Optional[PreviewClient] = None
        self.server: Optional[ServerInfo] = None
        self.stats = SessionStats()

        self.state: str = ConnectionState.IDLE
        self.error: Optional[str] = None
        self.error_code: Optional[str] = None
        self.reconnect_attempt = 0

        #: Set while connected so the app restores its own look after a preview
        #: session re-themed the native layer.
        self.theme_applied_by_remote = False
        self.remote_title: str = ""

        #: True once the session has been live at least once, so a later failure
        #: is a *drop* (the dev server went away) rather than a bad scan.
        self.was_live = False
        #: True when a live session dropped and could not be re-established;
        #: the preview screen turns this into the "not responding" dialog.
        self.dropped = False

        #: Callables invoked (on the caller's thread) after a disconnect.
        self.on_disconnect_hooks: list = []
        #: Callables invoked (on the UI thread) after every state change, with
        #: the new state string. The connect flow uses this to resolve.
        self.on_state_hooks: list = []

        #: Coalesces the UI rebuilds driven by render transactions: while a
        #: rebuild is queued, further transactions only advance the mirrored
        #: tree (and the counters), never the queue.
        self._refresh_pending = False
        self._refresh_lock = threading.Lock()

        self._closing = False

    # ── queries ───────────────────────────────────────────────────────────

    @property
    def is_live(self) -> bool:
        """True while a session is connected or resynchronising."""
        return self.state in (ConnectionState.CONNECTED,
                              ConnectionState.SYNCING)

    @property
    def is_busy(self) -> bool:
        """True while a connection attempt of any kind is in flight."""
        return self.state in (ConnectionState.CONNECTING,
                              ConnectionState.HANDSHAKING,
                              ConnectionState.RECONNECTING)

    @property
    def project_name(self) -> str:
        if self.server and self.server.project_name:
            return self.server.project_name
        if self.endpoint and self.endpoint.project_name:
            return self.endpoint.project_name
        return "Pydrud project"

    def describe_error(self) -> str:
        if not self.error:
            return ""
        code = f" ({self.error_code})" if self.error_code else ""
        return f"{self.error}{code}"

    # ── connecting ────────────────────────────────────────────────────────

    def connect(self, endpoint: Endpoint) -> None:
        """Open (or replace) a preview session from *endpoint*.

        Returns immediately; the connection work happens on a daemon thread and
        progress lands in the reactive state.
        """
        if self.is_busy:
            return
        self._teardown_client()
        self.endpoint = endpoint
        self.error = None
        self.error_code = None
        self.reconnect_attempt = 0
        self.remote_title = ""
        self.dropped = False
        last_endpoint.value = endpoint.as_dict()
        self._spawn_connect(initial=True)

    def reconnect(self) -> None:
        """User-requested retry of the stored endpoint."""
        if self.endpoint is None or self.is_busy:
            return
        self.error = None
        self.error_code = None
        self.reconnect_attempt = 0
        self.dropped = False
        self._spawn_connect(initial=True)

    def _spawn_connect(self, *, initial: bool) -> None:
        def worker():
            try:
                self._run_client()
            except PreviewHandshakeError as exc:
                self._set_state(ConnectionState.FAILED,
                                error=exc.message, code=exc.code)
            except (OSError, ConnectionError) as exc:
                self._handle_link_failure(str(exc), initial=initial)
            except Exception as exc:  # defensive: never kill the app
                self._set_state(ConnectionState.FAILED, error=str(exc))

        threading.Thread(target=worker, daemon=True,
                         name="pydash-preview-connect").start()

    def _run_client(self) -> None:
        """Blocking connect + handshake on the worker thread."""
        client = PreviewClient(
            self.endpoint,
            self.tree,
            on_state=self._on_client_state,
            on_transaction=self._on_transaction,
            on_command=self._on_remote_command,
            on_disconnect=self._on_link_lost,
        )
        self.client = client
        self.server = client.connect(metrics=_current_metrics())
        self.was_live = True
        self.dropped = False
        self._set_state(ConnectionState.CONNECTED)
        self.reconnect_attempt = 0
        self._remember_recent()

    def _remember_recent(self) -> None:
        """Add this endpoint to the recent-apps list on a successful connect.

        Done here — at the one place every entry point (scan, pasted URL, a
        recent row, a deep link) ends up — so the list is complete no matter
        how the session was started. Marshalled onto the UI thread because it
        touches reactive state and the storage service.
        """
        endpoint = self.endpoint
        if endpoint is None:
            return
        try:
            from app import recents
        except Exception:  # pragma: no cover - import is cheap and safe
            return
        on_ui(recents.remember, endpoint)

    # ── disconnecting ─────────────────────────────────────────────────────

    def disconnect(self, *, reason: Optional[str] = None) -> None:
        """Close the session and return Pydash to its own look."""
        self._closing = True
        self._teardown_client()
        self.tree.reset()
        self.stats = SessionStats()
        self.server = None
        self.remote_title = ""
        self.reconnect_attempt = 0
        self.was_live = False
        self.dropped = False
        self._set_state(ConnectionState.DISCONNECTED, error=reason)
        self._closing = False
        for hook in list(self.on_disconnect_hooks):
            try:
                hook()
            except Exception:
                pass

    def _teardown_client(self) -> None:
        if self.client is not None:
            self.client.disconnect("closed by user")
            self.client = None

    # ── callbacks (invoked on the client's threads) ───────────────────────

    def _on_client_state(self, state: str, detail: Optional[str]) -> None:
        if state == "connecting":
            self._set_state(ConnectionState.CONNECTING)
        elif state == "handshaking":
            self._set_state(ConnectionState.HANDSHAKING)

    def _on_transaction(self, kind: str, ops: int) -> None:
        """Record a render transaction, coalescing bursts into one rebuild.

        A project running an animation loop (the Heartbeat starter, a chart, a
        spinner) emits a transaction every frame. Queuing a UI rebuild for each
        one floods the app's single, bounded UI queue and eventually makes
        ``run_on_ui`` raise ``queue.Full`` on the reader thread — which tore
        the session down and left the preview blank the moment a button started
        an animation. Only the *newest* tree is ever displayed, so a rebuild
        that is already in flight absorbs any further transactions: the flag is
        cleared as the flush begins and the next transaction schedules the next
        flush. The counters still advance for every transaction.
        """
        self.stats.mark_sync(kind, ops)
        with self._refresh_lock:
            if self._refresh_pending:
                return
            self._refresh_pending = True
        on_ui(self._flush_transactions)

    def _flush_transactions(self) -> None:
        """Rebuild the preview from the latest mirrored tree (UI thread)."""
        with self._refresh_lock:
            self._refresh_pending = False
        self.state = ConnectionState.CONNECTED
        bump()
        refresh()

    def _on_remote_command(self, message: dict) -> None:
        """Handle one page command from the development server.

        Called on the client's reader thread for everything that is not a render
        transaction: theme pushes, toasts, snackbars, dialogs, native service
        calls, back results… The renderer layer owns the semantics.
        """
        from app.preview.renderer import handle_remote_command
        handle_remote_command(message)

    def _on_link_lost(self, reason: Optional[str]) -> None:
        if self._closing:
            return
        self._handle_link_failure(reason or "connection lost", initial=False)

    # ── link failures & auto-reconnect ────────────────────────────────────

    def _handle_link_failure(self, reason: str, *, initial: bool) -> None:
        if self._closing:
            return
        if initial:
            self._set_state(ConnectionState.FAILED,
                            error=self._friendly_error(reason))
            return
        # The link dropped after the session was live: this is the dev server
        # going away, which the preview screen reports as "not responding".
        self.dropped = True
        if not auto_reconnect.value:
            self._set_state(ConnectionState.DISCONNECTED, error=reason)
            return
        self.reconnect_attempt += 1
        if self.reconnect_attempt > RECONNECT_MAX_ATTEMPTS:
            self._set_state(
                ConnectionState.FAILED,
                error="The development server stopped responding. Check that "
                      "`pydrud dev` is still running.")
            return
        self._set_state(ConnectionState.RECONNECTING, error=reason)
        delay = min(RECONNECT_BASE_DELAY * (2 ** (self.reconnect_attempt - 1)),
                    RECONNECT_MAX_DELAY)

        def retry():
            if self.state != ConnectionState.RECONNECTING:
                return
            self._spawn_connect(initial=False)

        after(delay, retry)

    @staticmethod
    def _friendly_error(reason: str) -> str:
        text = str(reason or "connection failed")
        if "refused" in text:
            return ("The development server refused the connection. Is "
                    "`pydrud dev` still running, and are both devices on the "
                    "same network?")
        if "timed out" in text or "timeout" in text:
            return ("Could not reach the development server in time. Check the "
                    "network and any firewall on port 8597.")
        if "No route to host" in text or "unreachable" in text:
            return ("The development machine is unreachable. Both devices must "
                    "be on the same Wi-Fi network.")
        return text

    # ── state plumbing ────────────────────────────────────────────────────

    def _set_state(self, state: str, *, error: Optional[str] = None,
                   code: Optional[str] = None) -> None:
        def publish():
            self.state = state
            self.error = error
            self.error_code = code
            bump()
            refresh()
            for hook in list(self.on_state_hooks):
                try:
                    hook(state)
                except Exception:
                    pass
        on_ui(publish)

    # ── haptics ───────────────────────────────────────────────────────────

    def pulse_haptic(self, kind: str = "light") -> None:
        """Fire a small haptic tick if the user allows it."""
        if not haptics_enabled.value:
            return
        from app.runtime import current

        app = current()
        page = app.page if app is not None else None
        if page is None:
            return
        try:
            page.haptics.selection()
        except Exception:
            pass


def _current_metrics() -> dict:
    """The live window metrics, as the server's ``ready`` event expects."""
    try:
        return dict(MediaQuery.of())
    except Exception:
        return {"width": 360, "height": 640, "density": 2.0}


#: The app-wide preview session.
session = PreviewSession()
