"""Tests for Pydash's persistence, the recent-apps list and the preview exit.

These cover the behaviour the settings/recents work introduced:

* preferences are read back **after** the native bridge connects (the first
  build runs before it, so a naive read is always lost);
* the recent list expires entries after 15 minutes;
* a preview opened via ``replace`` (a scan or a deep link) can still be closed;
* every app bar measures the same compact height.
"""

import os
import sys
import time
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

from pydrud import App  # noqa: E402
from pydrud.testing import AppTester  # noqa: E402

import app.preview.session  # noqa: E402, F401
from app import prefs, recents, state, theme  # noqa: E402
from app.main import main  # noqa: E402
from app.preview import session  # noqa: E402
from app.preview.models import ConnectionState, Endpoint  # noqa: E402
from app.runtime import bind, router  # noqa: E402
from app.screens.scan import manual_text, scan_error  # noqa: E402

# ``from app.preview import session`` binds the *instance* over the submodule
# name, so reach the real module through ``sys.modules`` to patch ``on_ui``.
session_mod = sys.modules["app.preview.session"]

_STYLESHEET = os.path.join(_ROOT, "src", "app", "theme.pss")


def _endpoint(host="127.0.0.1", port=1, name="Demo App"):
    return Endpoint(host=host, port=port, session_id="s", token="t",
                    project_id="p", project_name=name)


class _Harness(unittest.TestCase):
    def setUp(self):
        session.disconnect()
        session.endpoint = None
        session.server = None
        session.state = ConnectionState.IDLE
        session.dropped = False
        state.active_tab.value = 0
        state.theme_mode.value = "system"
        state.auto_reconnect.value = True
        state.haptics_enabled.value = True
        state.keep_awake.value = False
        state.connecting.value = False
        state.connecting_endpoint.value = None
        state.connecting_origin.value = ""
        state.connection_failed.value = None
        state.recents.value = []
        manual_text.value = ""
        scan_error.value = ""
        prefs._loaded = False
        router.reset()

        app = App(target=main, title="Pydash", dev_server=False,
                  stylesheet=_STYLESHEET)
        app.attach_router(router)
        bind(app)
        self._app = app

    def tearDown(self):
        session.disconnect()
        if getattr(self, "tester", None) is not None:
            self.tester.stop()

    def _boot(self, **responders):
        self.tester = AppTester(app=self._app)
        for cmd, value in responders.items():
            self.tester.device.on_command(cmd, value)
        self.tester.start()
        self.tester.settle()
        return self.tester


class TestPreferences(_Harness):
    def test_preferences_are_restored_once_the_bridge_is_up(self):
        tester = self._boot(prefs_get=lambda msg: (
            {"pd_theme_mode": "dark",
             "pd_auto_reconnect": False}.get(msg.get("key"))))
        self.assertTrue(self.tester._thread.is_alive())
        self.assertEqual(state.theme_mode.value, "dark")
        self.assertFalse(state.auto_reconnect.value)
        # The read really went out (it was not lost to the pre-connect build).
        keys = {r.get("key") for r in tester.device.requests
                if r.get("cmd") == "prefs_get"}
        self.assertIn("pd_theme_mode", keys)

    def test_a_missing_preference_keeps_the_default(self):
        self._boot(prefs_get=lambda msg: None)
        self.assertEqual(state.theme_mode.value, "system")
        self.assertTrue(state.auto_reconnect.value)

    def test_saving_writes_the_namespaced_key(self):
        tester = self._boot(prefs_get=lambda msg: None)
        tester.device.change("pd_nav", 1)
        tester.settle()
        tester.device.change("pd_theme_segmented", 2)
        tester.settle()
        sets = [r for r in tester.device.requests if r.get("cmd") == "prefs_set"]
        self.assertTrue(any(r.get("key") == "pd_theme_mode" and
                            r.get("value") == "dark" for r in sets))


class TestRecents(unittest.TestCase):
    def setUp(self):
        state.recents.value = []

    def test_remember_puts_the_newest_first_and_dedupes(self):
        recents.remember(_endpoint(name="One"))
        recents.remember(_endpoint(host="10.0.0.2", port=9, name="Two"))
        recents.remember(_endpoint(name="One"))   # same host/port → move up
        names = [e.get("project_name") for e in recents.entries()]
        self.assertEqual(names, ["One", "Two"])
        self.assertEqual(len(recents.entries()), 2)

    def test_entries_expire_after_the_ttl(self):
        now = time.time()
        state.recents.value = [
            {**_endpoint(name="Fresh").as_dict(), "last_used": now - 60},
            {**_endpoint(name="Stale").as_dict(),
             "last_used": now - recents.TTL_SECONDS - 1},
        ]
        self.assertTrue(recents.prune(now=now))
        names = [e.get("project_name") for e in recents.entries()]
        self.assertEqual(names, ["Fresh"])

    def test_prune_is_a_no_op_when_nothing_expired(self):
        now = time.time()
        state.recents.value = [
            {**_endpoint().as_dict(), "last_used": now}]
        self.assertFalse(recents.prune(now=now))

    def test_age_label_reads_naturally(self):
        now = time.time()
        self.assertEqual(
            recents.age_label({"last_used": now - 5}, now=now), "just now")
        self.assertEqual(
            recents.age_label({"last_used": now - 300}, now=now), "5m ago")
        self.assertEqual(
            recents.age_label({"last_used": now - 7200}, now=now), "2h ago")

    def test_a_corrupt_entry_is_dropped_not_crashed_on(self):
        state.recents.value = ["nonsense", {"host": "h", "port": 1}]
        self.assertTrue(recents.prune())
        self.assertEqual(recents.entries(), [])


class TestTransactionCoalescing(unittest.TestCase):
    """A busy project (an animation loop) must not flood the UI queue."""

    def setUp(self):
        session.disconnect()
        session._refresh_pending = False

    def _capture(self):
        """Replace the module's ``on_ui`` with a synchronous recorder."""
        scheduled = []
        original = session_mod.on_ui
        session_mod.on_ui = lambda fn, *a, **k: scheduled.append((fn, a, k))
        self.addCleanup(lambda: setattr(session_mod, "on_ui", original))
        return scheduled

    def test_a_burst_of_transactions_schedules_one_rebuild(self):
        scheduled = self._capture()
        for _ in range(120):                 # two seconds at 60 fps
            session._on_transaction("patch", 1)
        # Only one rebuild is queued for the whole burst; the newest tree wins.
        self.assertEqual(len(scheduled), 1)

    def test_the_next_transaction_after_a_flush_schedules_again(self):
        scheduled = self._capture()
        session._on_transaction("patch", 1)
        session._on_transaction("patch", 1)
        self.assertEqual(len(scheduled), 1)
        # Draining the queued flush lets the following transaction re-arm it.
        fn, args, kwargs = scheduled[0]
        fn(*args, **kwargs)
        session._on_transaction("patch", 1)
        self.assertEqual(len(scheduled), 2)

    def test_every_transaction_still_counts(self):
        self._capture()
        before = session.stats.patches
        for _ in range(10):
            session._on_transaction("patch", 2)
        self.assertEqual(session.stats.patches, before + 10)
        self.assertEqual(session.stats.applied_ops, 20)


class TestSessionRecents(unittest.TestCase):
    """A successful connect records the endpoint for Home's recent list."""

    def setUp(self):
        state.recents.value = []

    def test_a_successful_connect_remembers_the_endpoint(self):
        session.endpoint = _endpoint(name="Studio")
        scheduled = []
        original = session_mod.on_ui
        session_mod.on_ui = lambda fn, *a, **k: scheduled.append((fn, a, k))
        self.addCleanup(lambda: setattr(session_mod, "on_ui", original))

        session._remember_recent()
        self.assertEqual(len(scheduled), 1)
        fn, args, _ = scheduled[0]
        fn(*args)                            # run recents.remember "on the UI"
        self.assertEqual([e.get("project_name") for e in recents.entries()],
                         ["Studio"])


class TestRecentAppsScreen(_Harness):
    def test_a_recent_app_shows_on_home_and_starts_a_check(self):
        recents.remember(_endpoint(name="Studio"))
        tester = self._boot(prefs_get=lambda msg: None)
        self.assertTrue(tester.shows("Recent apps"))
        self.assertTrue(tester.shows("Studio"))

        tester.tap("pd_recent_0")
        self.assertTrue(state.connecting.value)
        self.assertEqual(state.connecting_origin.value, "home")
        # The row spins while the link is checked.
        self.assertTrue(tester.exists("pd_recent_spin_0"))

    def test_recents_stay_visible_while_a_session_is_live(self):
        recents.remember(_endpoint(name="Studio"))
        session.state = ConnectionState.CONNECTED
        session.endpoint = _endpoint(name="Live App")
        tester = self._boot(prefs_get=lambda msg: None)
        # The live card is showing…
        self.assertTrue(tester.exists("pd_live_card"))
        # …and the recent list is still there to switch from.
        self.assertTrue(tester.exists("pd_recent_0"))
        self.assertTrue(tester.shows("Studio"))

    def test_a_recent_row_is_a_single_line_tile(self):
        recents.remember(_endpoint(name="Studio"))
        tester = self._boot(prefs_get=lambda msg: None)
        self.assertTrue(tester.exists("pd_recent_0"))
        # No subtitle → the tile is one line tall, like a Settings link tile.
        self.assertIsNone(tester.prop("pd_recent_0", "subtitle"))
        # The freshness signal moved into the trailing slot instead.
        self.assertTrue(tester.exists("pd_recent_age_0"))
        self.assertTrue(tester.exists("pd_recent_chev_0"))


class TestTabNavigation(_Harness):
    def test_tapping_the_active_tab_does_not_rebuild(self):
        tester = self._boot(prefs_get=lambda msg: None)
        calls = []
        original = self._app.update

        def counted(*args, **kwargs):
            calls.append(1)
            return original(*args, **kwargs)

        self._app.update = counted
        self.addCleanup(lambda: setattr(self._app, "update", original))

        # The native bar re-reports the current selection when a patch is
        # applied; rebuilding for a tab already on screen is wasted work.
        tester.device.change("pd_nav", 0)
        tester.settle()
        self.assertEqual(calls, [])

        # Switching to the other tab still rebuilds exactly once.
        tester.device.change("pd_nav", 1)
        tester.settle()
        self.assertEqual(len(calls), 1)
        self.assertEqual(state.active_tab.value, 1)


class TestPreviewChrome(_Harness):
    def test_the_preview_bar_matches_the_previewed_theme(self):
        tester = self._boot(prefs_get=lambda msg: None)
        router.replace("preview")
        tester.settle()
        bar = tester.node("pd_preview_bar_wrap")
        self.assertIsNotNone(bar)
        # The chrome floats on the previewed project's background rather than
        # Pydash's surface colour, so it blends into the mirrored app.
        self.assertEqual(bar.style.get("bg"), theme.background())

    def test_adopting_the_palette_before_entering_builds_cleanly(self):
        from app.preview import renderer

        tester = self._boot(prefs_get=lambda msg: None)
        renderer._REMOTE_THEME.clear()
        renderer._REMOTE_THEME.update({"background": "#FF123456",
                                       "primary": "#FF654321"})
        renderer._adopted = False
        self.addCleanup(renderer._REMOTE_THEME.clear)
        self.addCleanup(setattr, renderer, "_adopted", False)

        # This is what the navigation helpers do. Adopting from *inside* the
        # route builder used to nest a render that duplicated the route's
        # widgets — "Duplicate Pydrud widget key 'pd_preview'" — and blanked
        # the preview. Entering after adopting must render one clean tree.
        renderer.adopt_remote_theme()
        router.replace("preview")
        tester.settle()

        self.assertEqual(router.current_route, "preview")
        self.assertTrue(tester.exists("pd_preview_body"))
        self.assertTrue(tester.exists("pd_preview_bar_wrap"))
        self.assertEqual(theme.background(), "#FF123456")
        self.assertEqual(
            tester.node("pd_preview_bar_wrap").style.get("bg"), "#FF123456")

    def test_adoption_is_idempotent_within_one_entry(self):
        from app.preview import renderer

        self._boot(prefs_get=lambda msg: None)
        renderer._REMOTE_THEME.clear()
        renderer._REMOTE_THEME.update({"background": "#FF0A0B0C"})
        renderer._adopted = False
        self.addCleanup(renderer._REMOTE_THEME.clear)
        self.addCleanup(setattr, renderer, "_adopted", False)

        renderer.adopt_remote_theme()
        self.assertTrue(renderer._adopted)
        # A second call is a no-op, so the per-frame rebuilds cannot re-theme.
        renderer.adopt_remote_theme()
        self.assertTrue(renderer._adopted)


class TestPreviewExit(_Harness):
    def test_close_leaves_a_preview_opened_with_replace(self):
        tester = self._boot(prefs_get=lambda msg: None)
        # A deep link (and a scan) *replaces* the current screen, so the
        # preview can be the only entry on the stack — pop() would be a no-op.
        router.replace("preview")
        tester.settle()
        self.assertEqual(router.current_route, "preview")
        self.assertEqual(router.history, ["preview"])

        tester.tap("pd_preview_close")
        self.assertEqual(router.current_route, "shell")

    def test_exit_session_disconnects_and_goes_home(self):
        tester = self._boot(prefs_get=lambda msg: None)
        router.replace("preview")
        tester.settle()
        session.state = ConnectionState.CONNECTED

        tester.tap("pd_preview_exit")
        self.assertEqual(router.current_route, "shell")
        self.assertEqual(session.state, ConnectionState.DISCONNECTED)


class TestCompactAppBars(_Harness):
    def test_every_app_bar_is_the_same_compact_height(self):
        tester = self._boot(prefs_get=lambda msg: None)

        def bar_height(key):
            node = tester.node(key)
            self.assertIsNotNone(node)
            return node.style.get("minHeight")

        home = bar_height("pd_bar._bar")
        # Home carries a leading mark and a scan action, yet must match the
        # title-only Settings bar.
        tester.device.change("pd_nav", 1)
        tester.settle()
        settings = bar_height("pd_bar._bar")
        self.assertEqual(home, settings)

        router.push("scan", mode="scan")
        tester.settle()
        self.assertEqual(bar_height("pd_scan_bar._bar"), home)

    def test_the_home_bar_stays_compact_with_its_action(self):
        tester = self._boot(prefs_get=lambda msg: None)
        bar = tester.node("pd_bar._bar")
        # A compact bar must not be stretched by the 48dp action control.
        self.assertLessEqual(bar.style.get("minHeight"), 56)


if __name__ == "__main__":
    unittest.main()
