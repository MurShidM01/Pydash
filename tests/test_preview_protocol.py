"""The preview client and session, against an in-process dev server.

A tiny socket server speaks the same frames ``pydrud dev`` does — the v1
authenticated handshake followed by renderer-v2 transactions — so the client
is exercised end to end without a device or the real host.
"""

import json
import os
import socket
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from app.config import (  # noqa: E402
    PREVIEW_PROTOCOL,
    PREVIEW_PROTOCOL_VERSION,
    RENDERER_PROTOCOL_VERSION,
)
from app.preview.client import PreviewClient, PreviewHandshakeError  # noqa: E402
from app.preview.mirror import RemoteTree  # noqa: E402
from app.preview.models import ConnectionState, Endpoint  # noqa: E402
from app.preview.session import PreviewSession  # noqa: E402


def _welcome(port, **overrides):
    message = {
        "type": "preview_welcome",
        "protocol": PREVIEW_PROTOCOL,
        "protocol_version": PREVIEW_PROTOCOL_VERSION,
        "renderer_protocol_version": RENDERER_PROTOCOL_VERSION,
        "session_id": "sess-1",
        "port": port,
        "project": {"id": "proj", "name": "Demo App"},
        "capabilities": {},
        "limits": {},
    }
    message.update(overrides)
    return message


def _snapshot(revision, tree):
    return {
        "cmd": "render_transaction",
        "protocol_version": RENDERER_PROTOCOL_VERSION,
        "transaction_id": f"tx{revision}",
        "revision": revision,
        "base_revision": 0,
        "kind": "snapshot",
        "tree": tree,
    }


def _patch(revision, base, ops):
    return {
        "cmd": "render_transaction",
        "protocol_version": RENDERER_PROTOCOL_VERSION,
        "transaction_id": f"tx{revision}",
        "revision": revision,
        "base_revision": base,
        "kind": "patch",
        "patches": ops,
    }


def _tree():
    return {
        "type": "Column", "key": "root", "props": {}, "style": {},
        "children": [{"type": "Text", "key": "hello", "props": {"value": "Hi"},
                      "style": {}, "children": []}],
    }


class FakeDevServer:
    """A one-connection stand-in for ``pydrud dev``."""

    def __init__(self, *, reject=None, welcome_overrides=None):
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", 0))
        self._server.listen(1)
        self.port = self._server.getsockname()[1]

        self.reject = reject
        self.welcome_overrides = dict(welcome_overrides or {})
        self.received: list = []
        self._conn = None
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self.connected = threading.Event()

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True,
                                        name="fake-dev-server")
        self._thread.start()
        return self

    def stop(self):
        self._running = False
        for sock in (self._conn, self._server):
            try:
                if sock:
                    sock.close()
            except OSError:
                pass
        if self._thread is not None:
            self._thread.join(timeout=2)

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()

    def send(self, payload: dict):
        conn = self._conn
        if conn is None:
            raise RuntimeError("no client connected")
        conn.sendall((json.dumps(payload) + "\n").encode("utf-8"))

    def wait_for(self, predicate, timeout=3.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                if predicate(list(self.received)):
                    return True
            time.sleep(0.01)
        return False

    def wait_connected(self, timeout=3.0):
        return self.connected.wait(timeout)

    def of_type(self, type_):
        with self._lock:
            return [m for m in self.received if m.get("type") == type_]

    # ── server loop ───────────────────────────────────────────────────────

    def _serve(self):
        try:
            conn, _ = self._server.accept()
        except OSError:
            return
        self._conn = conn
        self.connected.set()
        buffer = b""
        try:
            while self._running:
                data = conn.recv(65536)
                if not data:
                    break
                buffer += data
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    text = line.decode("utf-8").strip()
                    if text:
                        self._on_message(json.loads(text))
        except (OSError, ValueError):
            pass

    def _on_message(self, message: dict):
        with self._lock:
            self.received.append(message)
        if message.get("type") == "preview_hello":
            if self.reject is not None:
                self.send(self.reject)
            else:
                self.send(_welcome(self.port, **self.welcome_overrides))


def _endpoint(port):
    return Endpoint(host="127.0.0.1", port=port, session_id="sess-1",
                    token="tok", project_id="proj", project_name="Demo App")


class TestPreviewClient(unittest.TestCase):
    def setUp(self):
        self.server = FakeDevServer().start()
        self.addCleanup(self.server.stop)
        self.tree = RemoteTree()
        self.client = None

    def tearDown(self):
        if self.client is not None:
            self.client.disconnect()

    def _connect(self, **kwargs):
        self.client = PreviewClient(_endpoint(self.server.port), self.tree,
                                    **kwargs)
        return self.client.connect(metrics={"width": 400, "height": 800})

    def test_handshake_returns_the_server_info(self):
        info = self._connect()
        self.assertEqual(info.project_name, "Demo App")
        self.assertEqual(info.project_id, "proj")
        self.assertEqual(info.session_id, "sess-1")

    def test_the_hello_frame_is_authenticated(self):
        self._connect()
        self.assertTrue(self.server.wait_for(
            lambda msgs: any(m.get("type") == "preview_hello" for m in msgs)))
        hello = self.server.of_type("preview_hello")[0]
        self.assertEqual(hello["protocol"], PREVIEW_PROTOCOL)
        self.assertEqual(hello["session_id"], "sess-1")
        self.assertEqual(hello["token"], "tok")
        self.assertTrue(hello["capabilities"]["ack_nack"])

    def test_the_ready_frame_carries_capabilities_and_metrics(self):
        self._connect()
        self.assertTrue(self.server.wait_for(
            lambda msgs: any(m.get("type") == "ready" for m in msgs)))
        ready = self.server.of_type("ready")[0]
        self.assertEqual(ready["data"]["width"], 400)
        self.assertIn("capabilities", ready["data"])

    def test_a_snapshot_is_applied_and_acked(self):
        self._connect()
        self.server.send(_snapshot(1, _tree()))
        self.assertTrue(self.server.wait_for(
            lambda msgs: any(m.get("type") == "render_ack" for m in msgs)))
        self.assertEqual(self.tree.revision, 1)
        self.assertEqual(self.tree.snapshot_json()["key"], "root")

    def test_a_stale_patch_is_nacked(self):
        self._connect()
        self.server.send(_snapshot(1, _tree()))
        self.assertTrue(self.server.wait_for(
            lambda msgs: any(m.get("type") == "render_ack" for m in msgs)))
        self.server.send(_patch(2, 7, [{"op": "delete", "key": "hello",
                                        "parent_key": "root"}]))
        self.assertTrue(self.server.wait_for(
            lambda msgs: any(m.get("type") == "render_nack" for m in msgs)))
        nack = self.server.of_type("render_nack")[0]
        self.assertEqual(nack["data"]["code"], "stale_base")
        self.assertEqual(nack["data"]["native_revision"], 1)

    def test_events_are_forwarded_to_the_server(self):
        self._connect()
        self.client.send_event("btn", "click", {"x": 1})
        self.client.send_back()
        self.client.send_metrics({"width": 411, "height": 731})
        self.assertTrue(self.server.wait_for(
            lambda msgs: any(m.get("type") == "back" for m in msgs)
            and any(m.get("type") == "metrics" for m in msgs)))
        click = self.server.of_type("click")[0]
        self.assertEqual(click["key"], "btn")
        self.assertEqual(click["data"]["value"], {"x": 1})

    def test_a_rejection_raises_a_handshake_error(self):
        self.server.stop()
        self.server = FakeDevServer(reject={
            "type": "preview_reject", "code": "bad_token",
            "message": "the one-run key is wrong",
        }).start()
        self.addCleanup(self.server.stop)
        self.client = PreviewClient(_endpoint(self.server.port), self.tree)
        with self.assertRaises(PreviewHandshakeError) as ctx:
            self.client.connect()
        self.assertEqual(ctx.exception.code, "bad_token")

    def test_a_protocol_version_mismatch_raises(self):
        self.server.stop()
        self.server = FakeDevServer(
            welcome_overrides={"protocol_version": 99}).start()
        self.addCleanup(self.server.stop)
        self.client = PreviewClient(_endpoint(self.server.port), self.tree)
        with self.assertRaises(PreviewHandshakeError) as ctx:
            self.client.connect()
        self.assertEqual(ctx.exception.code, "unsupported_version")


class TestPreviewSession(unittest.TestCase):
    def setUp(self):
        self.server = FakeDevServer().start()
        self.addCleanup(self.server.stop)
        self.session = PreviewSession()
        self.addCleanup(self.session.disconnect)

    def _wait_state(self, state, timeout=3.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.session.state == state:
                return True
            time.sleep(0.01)
        return False

    def _wait_for(self, predicate, timeout=3.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if predicate():
                return True
            time.sleep(0.01)
        return False

    def test_a_session_connects_and_renders_the_project(self):
        self.session.connect(_endpoint(self.server.port))
        self.assertTrue(self.server.wait_for(
            lambda msgs: any(m.get("type") == "ready" for m in msgs)))
        self.assertTrue(self._wait_state(ConnectionState.CONNECTED))
        self.assertTrue(self.session.is_live)

        self.server.send(_snapshot(1, _tree()))
        self.assertTrue(self.server.wait_for(
            lambda msgs: any(m.get("type") == "render_ack" for m in msgs)))
        # The client writes the ack to the socket *before* it counts the
        # transaction, so the ack does not imply the counter has advanced —
        # wait for the counter itself rather than racing the reader thread.
        self.assertTrue(self._wait_for(
            lambda: self.session.stats.snapshots == 1))
        self.assertEqual(self.session.project_name, "Demo App")

    def test_a_session_disconnects_cleanly(self):
        self.session.connect(_endpoint(self.server.port))
        self.assertTrue(self._wait_state(ConnectionState.CONNECTED))
        self.session.disconnect()
        self.assertEqual(self.session.state, ConnectionState.DISCONNECTED)
        self.assertFalse(self.session.is_live)
        self.assertTrue(self.session.tree.is_empty)

    def test_a_refused_connection_fails_with_a_friendly_message(self):
        # Nothing is listening on this port.
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.bind(("127.0.0.1", 0))
        dead_port = probe.getsockname()[1]
        probe.close()

        self.session.connect(_endpoint(dead_port))
        self.assertTrue(self._wait_state(ConnectionState.FAILED))
        self.assertIn("refused", self.session.describe_error().lower())


if __name__ == "__main__":
    unittest.main()
