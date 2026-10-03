"""End-to-end preview protocol tests: Pydash's client vs a real App.

The harness in ``tests/preview_server_harness.py`` reproduces the
``pydrud dev`` server and hands the socket to a genuine
:class:`pydrud.App`, so these tests exercise the complete wire contract:
handshake, rejection codes, revisioned transactions, ACK/NACK, resync,
event forwarding, page commands and the native service bridge.
"""

import os
import sys
import threading
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from pydrud import App, Button, Column, State, Text  # noqa: E402

from tests.preview_server_harness import (  # noqa: E402
    HarnessSession, PreviewServerHarness,
)

from app.preview.client import PreviewClient, PreviewHandshakeError  # noqa: E402
from app.preview.mirror import RemoteTree  # noqa: E402
from app.preview.models import Endpoint  # noqa: E402

METRICS = {"width": 400, "height": 800, "density": 2.0}


def build_counter_app():
    """A small project whose button increments a bound State."""
    counter = State(0, name="counter")
    toasts = []
    dialogs = []

    def target(page):
        page.add(Column(children=[
            Text(f"Count: {counter.value}", key="count_text"),
            Button("+1", key="inc").on_click(lambda _e: _bump()),
            Button("toast", key="toast").on_click(lambda _e: _toast(page)),
            Button("ask", key="ask").on_click(lambda _e: _ask(page)),
        ], key="body"))

    def _bump():
        counter.value += 1

    def _toast(page):
        page.toast("hello from the project")
        toasts.append("sent")

    def _ask(page):
        page.dialog.confirm("Run the migration?", title="Continue?").then(
            lambda value: dialogs.append(value))

    app = App(target=target, title="Counter Project").bind(counter)
    return app, counter, toasts, dialogs


class PreviewProtocolCase(unittest.TestCase):
    """Shared plumbing: one harness server + one connected client."""

    def setUp(self):
        self.app, self.counter, self.toasts, self.dialogs = build_counter_app()
        self.session = HarnessSession.create(project_name="Counter Project")
        self.server = PreviewServerHarness(self.app, self.session).start()

        self.tree = RemoteTree()
        self.commands: list = []
        self.transactions: list = []
        self.client = PreviewClient(
            self.endpoint(), self.tree,
            on_command=self.commands.append,
            on_transaction=self._note_transaction,
        )

    def tearDown(self):
        try:
            self.client.disconnect("test teardown")
        except Exception:
            pass
        self.server.stop()
        try:
            self.app.stop()
        except Exception:
            pass

    def endpoint(self, **overrides) -> Endpoint:
        fields = dict(
            host="127.0.0.1", port=self.server.port,
            session_id=self.session.session_id,
            token=self.session.token,
            project_id=self.session.project_id,
            project_name=self.session.project_name,
        )
        fields.update(overrides)
        return Endpoint(**fields)

    def _note_transaction(self, kind, ops):
        # Runs on the client's reader thread immediately after apply(), and
        # only that thread ever applies transactions — so tree.revision here
        # is exactly the revision of the transaction just applied.
        self.transactions.append((kind, ops, self.tree.revision))

    # ── helpers ───────────────────────────────────────────────────────────

    def wait_for(self, predicate, timeout=5.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if predicate():
                    return True
            except Exception:
                pass
            time.sleep(0.02)
        return False

    def find(self, key):
        return self._find_in(self.tree.snapshot_json(), key)

    @staticmethod
    def _find_in(node, key):
        if node is None:
            return None
        if node.get("key") == key:
            return node
        for child in node.get("children") or []:
            found = PreviewProtocolCase._find_in(child, key)
            if found is not None:
                return found
        return None


class TestHandshake(PreviewProtocolCase):
    def test_welcome_carries_project_metadata(self):
        info = self.client.connect(metrics=METRICS)
        self.assertEqual(info.project_name, "Counter Project")
        self.assertEqual(info.session_id, self.session.session_id)
        self.assertTrue(info.capabilities.get("incremental_patches"))
        self.client.disconnect()

    def test_wrong_token_is_rejected(self):
        with self.assertRaises(PreviewHandshakeError) as ctx:
            self.client = PreviewClient(
                self.endpoint(token="wrong-token"), self.tree)
            self.client.connect(metrics=METRICS)
        self.assertEqual(ctx.exception.code, "authentication_failed")

    def test_wrong_session_is_rejected(self):
        with self.assertRaises(PreviewHandshakeError) as ctx:
            self.client = PreviewClient(
                self.endpoint(session_id="00000000-0000-0000-0000-000000000000"),
                self.tree)
            self.client.connect(metrics=METRICS)
        self.assertEqual(ctx.exception.code, "authentication_failed")

    def test_refused_connection_reports_failure(self):
        client = PreviewClient(
            Endpoint(host="127.0.0.1", port=1, session_id="s", token="t"),
            RemoteTree())
        with self.assertRaises(OSError):
            client.connect(metrics=METRICS)


class TestTransactions(PreviewProtocolCase):
    def test_snapshot_arrives_and_is_acked(self):
        self.client.connect(metrics=METRICS)
        self.assertTrue(self.wait_for(lambda: bool(self.transactions)),
                        "no snapshot arrived")
        # A fresh session starts with a full snapshot at revision 1. Assert
        # on the *first applied transaction* rather than the mirror's live
        # revision: our `ready` event legitimately makes the server re-render
        # (see test_stale_mirror_triggers_snapshot_resync), so by the time
        # this thread reads tree.revision a second snapshot may already have
        # been applied on the reader thread. Whether that has happened yet is
        # pure scheduling luck (and on Windows' coarse sleep granularity it
        # reliably has), so the old `self.assertEqual(self.tree.revision, 1)`
        # was inherently flaky.
        kind, _ops, revision = self.transactions[0]
        self.assertEqual(kind, "snapshot")
        self.assertEqual(revision, 1)
        self.assertFalse(self.tree.is_empty)
        self.assertEqual(self.find("count_text")["props"]["value"],
                         "Count: 0")
        # The server advances its confirmed revision only on our ACK.
        self.assertTrue(self.wait_for(
            lambda: self.app._confirmed_revision >= 1))
        self.client.disconnect()

    def test_click_event_round_trips_as_a_patch(self):
        self.client.connect(metrics=METRICS)
        self.assertTrue(self.wait_for(lambda: not self.tree.is_empty))
        self.assertTrue(self.client.send_event("click", "inc", {}))
        self.assertTrue(self.wait_for(
            lambda: self.find("count_text")["props"]["value"] == "Count: 1"),
            "patched text never arrived")
        self.assertGreaterEqual(self.tree.revision, 2)
        self.assertTrue(any(kind == "patch"
                            for kind, _ops, _rev in self.transactions))
        self.client.disconnect()

    def test_stale_mirror_triggers_snapshot_resync(self):
        self.client.connect(metrics=METRICS)
        self.assertTrue(self.wait_for(lambda: not self.tree.is_empty))
        # Let the server settle first: the client's `ready` event makes it
        # re-render once more, and that snapshot would overwrite our drift.
        self.assertTrue(self.wait_for(
            lambda: self.app._confirmed_revision >= 1
            and not self.app._inflight
            and not self.app._render_pending))
        self.assertGreaterEqual(self.tree.revision, 1)
        # Pretend the mirror drifted (e.g. a patch was lost).
        with self.tree._lock:
            self.tree.revision = 99
        self.assertTrue(self.client.send_event("click", "inc", {}))
        self.assertTrue(self.wait_for(
            lambda: (self.find("count_text") or {}).get("props", {})
            .get("value") == "Count: 1"), "server never resynchronised")
        # The stale patch was refused, so recovery came as a snapshot whose
        # revision honours the 99 we reported in the NACK.
        self.assertGreaterEqual(self.tree.revision, 100)
        self.client.disconnect()

    def test_metrics_event_triggers_rerender(self):
        self.client.connect(metrics=METRICS)
        self.assertTrue(self.wait_for(lambda: not self.tree.is_empty))
        before = len(self.transactions)
        self.assertTrue(self.client.send_metrics({"width": 700,
                                                  "height": 900,
                                                  "density": 2.0}))
        self.assertTrue(self.wait_for(
            lambda: len(self.transactions) > before),
            "metrics event did not trigger a re-render")
        self.client.disconnect()

    def test_back_event_answers_back_result(self):
        self.client.connect(metrics=METRICS)
        self.assertTrue(self.wait_for(lambda: not self.tree.is_empty))
        self.assertTrue(self.client.send_back())
        self.assertTrue(self.wait_for(lambda: any(
            c.get("cmd") == "back_result" for c in self.commands)))
        result = [c for c in self.commands
                  if c.get("cmd") == "back_result"][-1]
        self.assertIsNotNone(result.get("handled"))
        self.client.disconnect()


class TestPageCommands(PreviewProtocolCase):
    def test_project_toast_reaches_the_client(self):
        self.client.connect(metrics=METRICS)
        self.assertTrue(self.wait_for(lambda: not self.tree.is_empty))
        self.assertTrue(self.client.send_event("click", "toast", {}))
        self.assertTrue(self.wait_for(lambda: bool(self.toasts)))
        self.client.disconnect()

    def test_project_dialog_uses_service_bridge(self):
        self.client.connect(metrics=METRICS)
        self.assertTrue(self.wait_for(lambda: not self.tree.is_empty))

        answered = threading.Event()

        def on_command(message):
            self.commands.append(message)
            if message.get("cmd") == "dialog" and "request_id" in message:
                # Answer exactly once, like the device would.
                self.client.send_result(
                    message["request_id"], ok=True, value=True)
                answered.set()

        self.client._on_command = on_command
        self.assertTrue(self.client.send_event("click", "ask", {}))
        self.assertTrue(self.wait_for(lambda: answered.is_set()
                                      and self.dialogs),
                        "dialog result never resolved on the project side")
        self.assertEqual(self.dialogs, [True])
        self.client.disconnect()

    def test_theme_command_is_forwarded(self):
        self.client.connect(metrics=METRICS)
        self.assertTrue(self.wait_for(
            lambda: any(c.get("cmd") == "theme" for c in self.commands)))
        theme = [c for c in self.commands if c.get("cmd") == "theme"][-1]
        self.assertIn("primary", theme)
        self.client.disconnect()


class TestPreviewSession(PreviewProtocolCase):
    """The full session stack — :class:`PreviewSession` over the client.

    Regression test for the crash where ``PreviewSession`` handed the
    client an ``on_command`` callback it never defined: every connect
    attempt died with ``'PreviewSession' object has no
    '_on_remote_command'`` and the preview screen showed "Preview
    unavailable".
    """

    def tearDown(self):
        # Drop the session before the harness server and its App stop.
        pysession = getattr(self, "pysession", None)
        if pysession is not None:
            try:
                pysession.disconnect("test teardown")
            except Exception:
                pass
        super().tearDown()

    def test_session_connects_and_routes_page_commands(self):
        from app.preview import renderer
        from app.preview.models import ConnectionState
        from app.preview.session import PreviewSession

        # In production, page commands go to *Pydash's* page (the native
        # bridge). In this test the only App in process is the previewed
        # one, and forwarding its theme push back to itself would loop the
        # socket — so neutralise the page and just watch the routing.
        routed: list = []
        real_handler = renderer.handle_remote_command

        def spy(message):
            routed.append(dict(message))
            real_handler(message)

        with mock.patch.object(renderer, "handle_remote_command", spy), \
                mock.patch.object(renderer, "_page", return_value=None):
            self.pysession = PreviewSession()
            self.pysession.connect(self.endpoint())

            self.assertTrue(self.wait_for(
                lambda: self.pysession.state == ConnectionState.CONNECTED),
                f"session never connected: "
                f"{self.pysession.describe_error()!r}")
            self.assertIsNone(self.pysession.error)
            self.assertEqual(self.pysession.project_name, "Counter Project")

            # The first snapshot lands in the mirror…
            self.assertTrue(self.wait_for(
                lambda: not self.pysession.tree.is_empty))

            # …and the server's theme push reaches the renderer layer —
            # this is the callback that used to be missing.
            self.assertTrue(self.wait_for(
                lambda: any(m.get("cmd") == "theme" for m in routed)),
                "page commands never reached the renderer")

    def test_session_reports_handshake_rejection(self):
        from app.preview.models import ConnectionState
        from app.preview.session import PreviewSession

        self.pysession = PreviewSession()
        self.pysession.connect(self.endpoint(token="wrong-token"))
        self.assertTrue(self.wait_for(
            lambda: self.pysession.state == ConnectionState.FAILED))
        self.assertEqual(self.pysession.error_code, "authentication_failed")


if __name__ == "__main__":
    unittest.main()
