"""End-to-end tests for Pydash.

``AppTester`` boots the app against a protocol reference renderer, so these run
without an emulator or a platform build toolchain. They cover the shell and its
two tabs, the theme switch, the scan flow's validation and the deep-link path
into a live session.
"""

import os
import sys
import time
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

from pydrud import App  # noqa: E402
from pydrud.testing import AppTester  # noqa: E402

from app import state  # noqa: E402
from app.main import main  # noqa: E402
from app.preview import session  # noqa: E402
from app.preview.models import ConnectionState  # noqa: E402
from app.preview.uri import build_uri  # noqa: E402
from app.runtime import bind, router  # noqa: E402
from app.screens.scan import manual_text, scan_error  # noqa: E402

_STYLESHEET = os.path.join(_ROOT, "src", "app", "theme.pss")


def _valid_uri(host="127.0.0.1", port=1):
    return build_uri(host=host, port=port, session_id="sess-1",
                     token="tok", project_id="proj", project_name="Demo App")


class TestApp(unittest.TestCase):
    def setUp(self):
        session.disconnect()
        session.endpoint = None
        session.server = None
        session.state = ConnectionState.IDLE
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
        session.dropped = False
        manual_text.value = ""
        scan_error.value = ""
        router.reset()

        app = App(target=main, title="Pydash", dev_server=False,
                  stylesheet=_STYLESHEET)
        app.attach_router(router)
        bind(app)
        self.app = AppTester(app=app).start()

    def tearDown(self):
        session.disconnect()
        self.app.stop()

    def _wait(self, predicate, timeout=2.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if predicate():
                return True
            time.sleep(0.01)
        return False

    # ── shell ─────────────────────────────────────────────────────────────

    def test_home_is_the_default_screen(self):
        self.assertTrue(self.app.shows("Pydash"))
        self.assertTrue(self.app.shows("Scan QR code"))
        self.assertTrue(self.app.shows("Enter connection URL"))
        self.assertTrue(self.app.shows("How it works"))
        for key in ("pd_shell._body", "pd_hero", "pd_nav", "pd_home",
                    "pd_bar_scan"):
            with self.subTest(key=key):
                self.assertTrue(self.app.exists(key))

    def test_the_bottom_navigation_switches_to_settings(self):
        self.app.device.change("pd_nav", 1)
        self.app.settle()
        self.assertEqual(state.active_tab.value, 1)
        self.assertTrue(self.app.shows("Appearance"))
        self.assertTrue(self.app.shows("About"))
        self.assertTrue(self.app.shows("Theme mode"))

        self.app.device.change("pd_nav", 0)
        self.app.settle()
        self.assertEqual(state.active_tab.value, 0)
        self.assertTrue(self.app.shows("Scan QR code"))

    def test_the_stylesheet_styles_the_screen(self):
        from pydrud.core.styles.parser import parse_pss

        with open(_STYLESHEET, encoding="utf-8") as handle:
            sheet = parse_pss(handle.read(), filename="theme.pss")
        self.assertFalse([d for d in sheet.diagnostics if d.kind == "error"])
        self.assertGreater(len(sheet.rules), 10)

        hero = self.app.node("pd_hero")
        self.assertIsNotNone(hero)
        self.assertIn("gradient", hero.style)
        self.assertEqual(self.app.node("pd_hero_title").style["font"]["size"],
                         22)

    # ── theme ─────────────────────────────────────────────────────────────

    def test_the_theme_switch_updates_the_mode(self):
        self.app.device.change("pd_nav", 1)
        self.app.settle()

        self.app.device.change("pd_theme_segmented", 2)
        self.app.settle()
        self.assertEqual(state.theme_mode.value, "dark")

        self.app.device.change("pd_theme_segmented", 1)
        self.app.settle()
        self.assertEqual(state.theme_mode.value, "light")

    def test_behaviour_switches_flip_their_state(self):
        self.app.device.change("pd_nav", 1)
        self.app.settle()

        self.assertTrue(state.haptics_enabled.value)
        self.app.device.change("pd_control_haptics", False)
        self.app.settle()
        self.assertFalse(state.haptics_enabled.value)

    # ── scanning & manual entry ───────────────────────────────────────────

    def test_manual_entry_rejects_a_bad_url(self):
        router.push("scan", mode="manual")
        self.app.settle()
        self.assertTrue(self.app.shows("Connection URL"))

        self.app.type_in("pd_manual_field", "not a preview url")
        self.app.tap("Connect")
        self.assertTrue(self.app.shows("That code didn't work"))
        self.assertIsNone(session.endpoint)

    def test_manual_entry_accepts_a_valid_url(self):
        router.push("scan", mode="manual")
        self.app.settle()

        self.app.type_in("pd_manual_field", _valid_uri())
        self.app.tap("Connect")
        # The screen stays put and spins while the handshake runs, rather than
        # dropping the user onto an empty preview stage.
        self.assertTrue(self.app.exists("pd_scan_connecting"))
        self.assertEqual(router.current_route, "scan")
        self.assertIsNotNone(session.endpoint)
        self.assertEqual(session.endpoint.host, "127.0.0.1")

        # Nothing is listening on port 1, so the attempt fails and the app
        # asks the user what to do instead of hanging on the spinner.
        self.assertTrue(self._wait(
            lambda: self.app.exists("pd_not_responding"), timeout=8.0))
        self.assertEqual(router.current_route, "scan")

    def test_the_not_responding_dialog_goes_home(self):
        router.push("scan", mode="manual")
        self.app.settle()
        self.app.type_in("pd_manual_field", _valid_uri())
        self.app.tap("Connect")
        self.assertTrue(self._wait(
            lambda: self.app.exists("pd_not_responding"), timeout=8.0))

        self.app.device.send_event("click", "pd_not_responding",
                                   {"action": "home"})
        self.app.settle()
        self.assertTrue(self._wait(lambda: router.current_route == "shell"))
        self.assertIsNone(state.connection_failed.value)

    def test_the_scanner_screen_offers_both_ways_in(self):
        router.push("scan", mode="scan")
        self.app.settle()
        self.assertTrue(self.app.exists("pd_scanner"))
        self.assertTrue(self.app.shows("Enter the URL manually"))

        self.app.tap("Enter the URL manually")
        self.assertTrue(self.app.shows("Connection URL"))

    # ── deep links ────────────────────────────────────────────────────────

    def test_a_deep_link_opens_a_session(self):
        link = ("pydash://preview/connect?host=127.0.0.1&port=1"
                "&session=sess-1&token=tok&project=proj&name=Demo+App")
        router.handle_link(link)
        self.app.settle()
        self.assertTrue(self._wait(
            lambda: router.current_route == "preview"
            and session.endpoint is not None))
        self.assertEqual(session.endpoint.host, "127.0.0.1")
        self.assertEqual(session.endpoint.project_name, "Demo App")

    def test_a_broken_deep_link_returns_home(self):
        router.handle_link("pydash://preview/connect?host=127.0.0.1")
        self.app.settle()
        self.assertTrue(self._wait(lambda: router.current_route == "shell"))
        self.assertIsNone(session.endpoint)


if __name__ == "__main__":
    unittest.main()
