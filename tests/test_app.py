"""Tests for the Pydash app: shell, screens, navigation and interactions.

``AppTester`` boots the whole app (routes, tab shell, preview flow)
against a fake device, so these run anywhere — no emulator, no Gradle.
Run them with ``pydrud test`` or ``pytest``.
"""

import os
import sys
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


class TestApp(unittest.TestCase):
    def setUp(self):
        active_tab.value = 0
        session.state = ConnectionState.IDLE
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

    def test_preview_screen_explains_idle_state(self):
        router.push("preview")
        self.assertTrue(self.app.shows("No live session"))

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
