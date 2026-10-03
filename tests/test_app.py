"""Tests for the Pydash app: shell, screens, navigation and interactions.

``AppTester`` boots the whole app (routes, tab shell, preview flow)
against a fake device, so these run anywhere — no emulator, no Gradle.
Run them with ``pydrud test`` or ``pytest``.
"""

import copy
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from pydrud import Colors  # noqa: E402
from pydrud.testing import AppTester  # noqa: E402

from app.main import create_app  # noqa: E402
from app.preview.models import ConnectionState  # noqa: E402
from app.preview.session import session  # noqa: E402
from app.runtime import refresh, router  # noqa: E402
from app.state import active_tab  # noqa: E402

#: A miniature remote project: its own Scaffold with a text on it, as
#: ``pydrud dev`` would serialise it.
REMOTE_SNAPSHOT = {
    "type": "Scaffold",
    "key": "remote_root",
    "style": {"width": "match", "height": "match"},
    "props": {},
    "children": [
        {"type": "Text", "key": "remote_greeting", "style": {},
         "props": {"value": "Hello from dev"}, "children": []},
    ],
}


class TestApp(unittest.TestCase):
    def setUp(self):
        active_tab.value = 0
        session.state = ConnectionState.IDLE
        session.tree.reset()
        self.app = AppTester(app=create_app()).start()

    def tearDown(self):
        self.app.stop()

    # ── shell & tabs ─────────────────────────────────────────────────────

    def test_home_dashboard_renders(self):
        self.assertTrue(self.app.shows("Scan QR code"))
        self.assertTrue(self.app.shows("HOW IT WORKS"))
        self.assertTrue(self.app.shows("Connect manually"))

    def test_tabs_switch_content(self):
        self.app.toggle("pd_shell_nav", 1)
        self.assertTrue(self.app.shows("APPEARANCE"))
        self.app.toggle("pd_shell_nav", 0)
        self.assertTrue(self.app.shows("Scan QR code"))

    def test_app_bar_status_dot_red_when_not_connected(self):
        node = self.app.node("pd_shell_status_dot")
        self.assertIsNotNone(node)
        self.assertEqual(node.style.get("bg"), Colors.ERROR)
        self.assertIsNone(self.app.node("pd_shell_status_label"))

    def test_app_bar_status_dot_green_when_connected(self):
        session.state = ConnectionState.CONNECTED
        try:
            refresh()
            self.app.device.wait_for(
                lambda d: (d.find_key("pd_shell_status_dot") or {}).get(
                    "style", {}).get("bg") == Colors.SUCCESS
            )
            node = self.app.node("pd_shell_status_dot")
            self.assertIsNotNone(node)
            self.assertEqual(node.style.get("bg"), Colors.SUCCESS)
        finally:
            session.state = ConnectionState.IDLE
            refresh()

    # ── connection flow screens ──────────────────────────────────────────

    def test_scan_screen_shows_camera_and_manual_entry(self):
        router.push("scan")
        self.assertTrue(self.app.shows("Connect to a dev server"))

    def test_scan_manual_mode_prefills_uri_entry(self):
        router.push("scan", mode="manual")
        self.assertTrue(self.app.shows("PASTE THE CONNECTION URI"))

    def test_scan_screen_resets_to_camera_mode_after_manual_mode(self):
        # 1. Open manual mode
        router.push("scan", mode="manual")
        self.assertTrue(self.app.shows("PASTE THE CONNECTION URI"))

        # 2. Go back to Home
        router.pop()
        self.assertTrue(self.app.shows("Scan QR code"))

        # 3. Open scan screen again via "Scan QR code"
        router.push("scan")
        self.assertTrue(self.app.shows("Connect to a dev server"))
        self.assertFalse(self.app.shows("PASTE THE CONNECTION URI"))

    def test_scan_screen_mode_toggle_switches_between_camera_and_manual(self):
        router.push("scan")
        self.assertFalse(self.app.shows("PASTE THE CONNECTION URI"))

        # Switch to manual using toggle
        self.app.toggle("pd_scan_mode_toggle", 1)
        self.assertTrue(self.app.shows("PASTE THE CONNECTION URI"))

        # Switch back to camera using toggle
        self.app.toggle("pd_scan_mode_toggle", 0)
        self.assertFalse(self.app.shows("PASTE THE CONNECTION URI"))

        # Switch to manual using manual link
        self.app.tap("pd_scan_manual_link")
        self.assertTrue(self.app.shows("PASTE THE CONNECTION URI"))

        # Switch back to camera using switch camera button
        self.app.tap("pd_scan_switch_camera")
        self.assertFalse(self.app.shows("PASTE THE CONNECTION URI"))

    def test_home_scan_and_manual_buttons_navigate_to_correct_modes(self):
        # Tap 'Connect manually' on home
        self.app.tap("pd_home_manual")
        self.assertTrue(self.app.shows("PASTE THE CONNECTION URI"))

        # Go back
        self.app.tap("pd_scan_back")
        self.assertTrue(self.app.shows("Scan QR code"))

        # Tap 'Scan QR code' on home
        self.app.tap("pd_home_scan")
        self.assertTrue(self.app.shows("Connect to a dev server"))
        self.assertFalse(self.app.shows("PASTE THE CONNECTION URI"))

    def test_preview_screen_explains_idle_state(self):
        router.push("preview")
        self.assertTrue(self.app.shows("No live session"))
        self.assertIsNotNone(self.app.node("pd_preview_bar"))

    def test_preview_is_immersive_once_the_snapshot_arrives(self):
        session.tree.apply(revision=1, base_revision=0, kind="snapshot",
                           payload={"tree": copy.deepcopy(REMOTE_SNAPSHOT)})
        session.state = ConnectionState.CONNECTED
        try:
            router.push("preview")
            self.assertTrue(self.app.shows("Hello from dev"))
            # The remote project renders…
            self.assertIsNotNone(self.app.node("pd_preview_host"))
            self.assertIsNotNone(self.app.node("remote_root"))
            # …and owns the whole screen: none of Pydash's own chrome
            # (top bar, footer) is showing while it does.
            self.assertIsNone(self.app.node("pd_preview_bar"))
            self.assertIsNone(self.app.node("pd_preview_bar_row"))
            self.assertIsNone(self.app.node("pd_preview_footer"))
        finally:
            session.tree.reset()
            session.state = ConnectionState.IDLE
            router.reset("shell")
            refresh()

    def test_preview_keeps_chrome_while_waiting_for_first_snapshot(self):
        session.state = ConnectionState.CONNECTED
        try:
            router.push("preview")
            self.assertTrue(self.app.device.wait_for(
                lambda d: d.root is not None
                and d.root.find("pd_preview_bar") is not None))
            self.assertIsNotNone(self.app.node("pd_preview_bar"))
            self.assertIsNone(self.app.node("pd_preview_host"))
        finally:
            session.state = ConnectionState.IDLE
            router.reset("shell")
            refresh()

    def test_second_back_press_exits_when_project_never_answers(self):
        from app.preview import renderer

        session.tree.apply(revision=1, base_revision=0, kind="snapshot",
                           payload={"tree": copy.deepcopy(REMOTE_SNAPSHOT)})
        session.state = ConnectionState.CONNECTED

        class StubClient:
            is_connected = True

            def send_back(self):
                return True

            def disconnect(self, reason=None):
                pass

        session.client = StubClient()
        try:
            router.push("preview")
            self.assertTrue(self.app.device.wait_for(
                lambda d: d.root is not None
                and d.root.find("pd_preview_host") is not None))
            # A back offer sent long ago that the project never answered
            # (paused debugger, hung handler) must not trap the user.
            renderer._back_offered_at = time.time() - 5
            renderer.handle_back()
            self.assertEqual(router.current_route, "shell")
        finally:
            session.client = None
            renderer._back_offered_at = None
            session.tree.reset()
            session.state = ConnectionState.IDLE
            router.reset("shell")
            refresh()

    def test_settings_screen_lists_protocol_info(self):
        self.app.toggle("pd_shell_nav", 1)
        self.assertTrue(self.app.shows("RUNTIME & PROTOCOL"))
        self.assertTrue(self.app.shows("Preview protocol"))

    # ── deep links ───────────────────────────────────────────────────────

    def test_unknown_deep_link_shows_not_found(self):
        router.go("/definitely/not/a/route")
        self.assertTrue(self.app.shows("Nothing here"))


if __name__ == "__main__":
    unittest.main()
