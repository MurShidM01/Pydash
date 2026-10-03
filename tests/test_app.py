"""Tests for the Pydash app: shell, screens, navigation and interactions.

``AppTester`` boots the whole app (routes, tab shell, catalog, playground)
against a fake device, so these run anywhere — no emulator, no Gradle.
Run them with ``pydrud test`` or ``pytest``.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from pydrud.testing import AppTester  # noqa: E402

from app.main import create_app  # noqa: E402
from app.runtime import router  # noqa: E402
from app.state import active_tab, catalog_query  # noqa: E402


class TestApp(unittest.TestCase):
    def setUp(self):
        active_tab.value = 0
        catalog_query.value = ""
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
        self.assertTrue(self.app.shows("Typography"))
        self.app.toggle("pd_shell_nav", 3)
        self.assertTrue(self.app.shows("APPEARANCE"))
        self.app.toggle("pd_shell_nav", 0)
        self.assertTrue(self.app.shows("Scan QR code"))

    def test_status_pill_reflects_idle_state(self):
        node = self.app.node("pd_shell_status_label")
        self.assertIsNotNone(node)
        self.assertEqual(node.props.get("value"), "Not connected")

    # ── components catalog ───────────────────────────────────────────────

    def test_catalog_lists_every_category(self):
        self.app.toggle("pd_shell_nav", 1)
        for name in ("Typography", "Buttons", "Inputs & forms",
                     "Lists & cards", "Motion & gestures", "Canvas & charts"):
            self.assertTrue(self.app.shows(name), msg=name)

    def test_catalog_search_filters_cards(self):
        self.app.toggle("pd_shell_nav", 1)
        self.app.type_in("pd_cat_search", "chip")
        self.assertTrue(self.app.shows("Chips & badges"))
        self.assertNotIn("Typography", self.app.texts)

    def test_category_screen_builds_every_demo(self):
        router.push("category", cat="buttons")
        self.assertTrue(self.app.shows("Variants & sizes"))
        self.assertTrue(self.app.shows("Floating action button"))

    # ── playground ───────────────────────────────────────────────────────

    def test_playground_index_lists_demos(self):
        self.app.toggle("pd_shell_nav", 2)
        self.assertTrue(self.app.shows("Reactive State"))
        self.assertTrue(self.app.shows("Kitchen Sink"))

    def test_state_demo_counter_increments(self):
        router.push("demo", id="state")
        self.assertTrue(self.app.shows("COUNTER"))
        self.assertEqual(
            self.app.prop("pd_demo_state_body_value", "value"), "0")
        self.app.tap("pd_demo_state_body_inc")
        self.assertEqual(
            self.app.prop("pd_demo_state_body_value", "value"), "1")
        self.app.tap("pd_demo_state_body_inc")
        self.assertEqual(
            self.app.prop("pd_demo_state_body_value", "value"), "2")

    def test_state_demo_reset_uses_snackbar(self):
        router.push("demo", id="state")
        self.assertTrue(self.app.shows("COUNTER"))
        self.app.tap("pd_demo_state_body_inc")
        self.app.tap("pd_demo_state_body_reset")
        self.assertEqual(
            self.app.prop("pd_demo_state_body_value", "value"), "0")
        self.assertTrue(self.app.device.wait_for_command("snackbar"))

    def test_navigation_demo_pushes_item_screen(self):
        router.push("demo", id="navigation")
        self.assertTrue(self.app.shows("Push a screen onto the stack"))
        self.app.tap("pd_demo_navigation_body_slide")
        self.assertTrue(self.app.shows("You pushed item 1"))
        self.assertTrue(self.app.press_back())

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
        self.app.toggle("pd_shell_nav", 3)
        self.assertTrue(self.app.shows("RUNTIME & PROTOCOL"))
        self.assertTrue(self.app.shows("Preview protocol"))

    # ── deep links ───────────────────────────────────────────────────────

    def test_unknown_deep_link_shows_not_found(self):
        router.go("/definitely/not/a/route")
        self.assertTrue(self.app.shows("Nothing here"))


if __name__ == "__main__":
    unittest.main()
