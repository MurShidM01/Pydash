"""Tests for the mirrored remote tree and patch applier.

The mirror must reproduce, for JSON trees, the semantics the Android
``ViewFactory.applyPatch`` implements for native views — including the
stale-base guard that drives resynchronisation. The property test below
drives it with patches produced by Pydrud's *real* diff engine.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from pydrud import Button, Column, Text  # noqa: E402
from pydrud.core.diff import TreeDiff  # noqa: E402
from pydrud.core.protocol import RenderTransaction  # noqa: E402

from app.preview.mirror import (  # noqa: E402
    MirrorApplyError, MirrorWidget, RemoteTree,
)


def node(kind: str, key: str, *, props=None, style=None, children=None,
         events=None) -> dict:
    return {
        "type": kind, "key": key, "style": style or {},
        "expand": None, "visible": True, "tooltip": None,
        "has_events": bool(events), "events": list(events or []),
        "props": props or {}, "children": children or [],
    }


def sample_tree() -> dict:
    return node("Stack", "_page", children=[
        node("Column", "body", children=[
            node("Text", "title", props={"value": "Hello"}),
            node("Button", "btn", props={"text": "Go"}, events=["click"]),
        ]),
    ])


class TestRemoteTree(unittest.TestCase):
    def setUp(self):
        self.tree = RemoteTree()

    def test_starts_empty(self):
        self.assertTrue(self.tree.is_empty)
        self.assertEqual(self.tree.node_count(), 0)
        self.assertIsNone(self.tree.snapshot_json())

    def test_applies_snapshot(self):
        ops = self.tree.apply(revision=1, base_revision=0, kind="snapshot",
                              payload={"tree": sample_tree()})
        self.assertEqual(ops, 1)
        self.assertEqual(self.tree.revision, 1)
        self.assertEqual(self.tree.node_count(), 4)

    def test_rejects_snapshot_without_tree(self):
        with self.assertRaises(MirrorApplyError):
            self.tree.apply(revision=1, base_revision=0, kind="snapshot",
                            payload={"tree": None})

    def test_rejects_stale_patch(self):
        self.tree.apply(revision=1, base_revision=0, kind="snapshot",
                        payload={"tree": sample_tree()})
        with self.assertRaises(MirrorApplyError) as ctx:
            self.tree.apply(revision=2, base_revision=0, kind="patch",
                            payload={"patches": []})
        self.assertIn("stale_base_revision", str(ctx.exception))

    def test_rejects_unknown_kind(self):
        with self.assertRaises(MirrorApplyError):
            self.tree.apply(revision=1, base_revision=0, kind="mystery",
                            payload={})

    # ── individual patch ops (ViewFactory semantics) ─────────────────────

    def _with_snapshot(self):
        self.tree.apply(revision=1, base_revision=0, kind="snapshot",
                        payload={"tree": sample_tree()})

    def _find(self, key):
        return _find_in(self.tree.snapshot_json(), key)

    def test_patch_create_inserts_at_index(self):
        self._with_snapshot()
        self.tree.apply(revision=2, base_revision=1, kind="patch",
                        payload={"patches": [{
                            "op": "create", "key": "sub",
                            "parent_key": "body", "index": 1,
                            "tree": node("Text", "sub",
                                         props={"value": "inserted"}),
                        }]})
        body = self._find("body")
        self.assertEqual([c["key"] for c in body["children"]],
                         ["title", "sub", "btn"])

    def test_patch_create_at_root_replaces_root(self):
        self._with_snapshot()
        self.tree.apply(revision=2, base_revision=1, kind="patch",
                        payload={"patches": [{
                            "op": "create", "key": "_page2",
                            "parent_key": "", "index": 0,
                            "tree": node("Stack", "_page2", children=[
                                node("Text", "solo",
                                     props={"value": "new root"})]),
                        }]})
        self.assertEqual(self.tree.snapshot_json()["key"], "_page2")

    def test_patch_delete_removes_subtree(self):
        self._with_snapshot()
        self.tree.apply(revision=2, base_revision=1, kind="patch",
                        payload={"patches": [{
                            "op": "delete", "key": "btn",
                            "parent_key": "body",
                        }]})
        body = self._find("body")
        self.assertEqual([c["key"] for c in body["children"]], ["title"])

    def test_patch_update_merges_props_and_style(self):
        self._with_snapshot()
        self.tree.apply(revision=2, base_revision=1, kind="patch",
                        payload={"patches": [{
                            "op": "update", "key": "title",
                            "parent_key": "body",
                            "props": {"value": "Changed"},
                            "style": {"opacity": 0.5},
                        }]})
        title = self._find("title")
        self.assertEqual(title["props"]["value"], "Changed")
        self.assertEqual(title["style"]["opacity"], 0.5)

    def test_patch_move_reorders(self):
        self._with_snapshot()
        self.tree.apply(revision=2, base_revision=1, kind="patch",
                        payload={"patches": [{
                            "op": "move", "key": "btn",
                            "parent_key": "body", "index": 0,
                        }]})
        body = self._find("body")
        self.assertEqual([c["key"] for c in body["children"]],
                         ["btn", "title"])

    def test_patch_replace_swaps_in_place(self):
        self._with_snapshot()
        self.tree.apply(revision=2, base_revision=1, kind="patch",
                        payload={"patches": [{
                            "op": "replace", "key": "btn",
                            "new_key": "link", "parent_key": "body",
                            "index": 1,
                            "tree": node("Text", "link",
                                         props={"value": "not a button"}),
                        }]})
        body = self._find("body")
        self.assertEqual([c["key"] for c in body["children"]],
                         ["title", "link"])

    def test_patch_unknown_parent_raises(self):
        self._with_snapshot()
        with self.assertRaises(MirrorApplyError):
            self.tree.apply(revision=2, base_revision=1, kind="patch",
                            payload={"patches": [{
                                "op": "create", "key": "orphan",
                                "parent_key": "missing", "index": 0,
                                "tree": node("Text", "orphan"),
                            }]})

    def test_patch_unknown_update_key_raises(self):
        self._with_snapshot()
        with self.assertRaises(MirrorApplyError):
            self.tree.apply(revision=2, base_revision=1, kind="patch",
                            payload={"patches": [{
                                "op": "update", "key": "ghost",
                                "parent_key": "body", "props": {},
                            }]})

    def test_reset_clears_everything(self):
        self._with_snapshot()
        self.tree.reset()
        self.assertTrue(self.tree.is_empty)
        self.assertEqual(self.tree.revision, 0)


class TestDiffRoundTrip(unittest.TestCase):
    """Patches from Pydrud's real diff engine apply cleanly to the mirror."""

    def _tree(self, text: str, extra=None):
        children = [Text(text, key="title")]
        if extra:
            children.append(Button(extra, key="extra"))
        return Column(children=children, key="body")

    def test_property_update(self):
        old = self._tree("Hello")
        new = self._tree("Goodbye")
        transaction = RenderTransaction.create(
            revision=2, base_revision=1, kind="patch",
            payload={"patches": [p.to_dict() for p in TreeDiff.diff(old, new)]})
        mirror = RemoteTree()
        mirror.apply(revision=1, base_revision=0, kind="snapshot",
                     payload={"tree": old.to_dict()})
        mirror.apply(revision=transaction.revision,
                     base_revision=transaction.base_revision,
                     kind="patch",
                     payload={"patches": transaction.payload["patches"]})
        self.assertEqual(
            _find_in(mirror.snapshot_json(), "title")["props"]["value"],
            "Goodbye")

    def test_property_insert_and_remove(self):
        old = self._tree("Hello", extra="Remove me")
        new = self._tree("Hello", extra=None)
        new.children = [c for c in new.children if c.key != "extra"]

        mirror = RemoteTree()
        mirror.apply(revision=1, base_revision=0, kind="snapshot",
                     payload={"tree": old.to_dict()})

        # Add then remove, through the real diff engine.
        grown = self._tree("Hello", extra="Remove me")
        grown.children.append(Text("appended", key="appended"))
        add_tx = RenderTransaction.create(
            revision=2, base_revision=1, kind="patch",
            payload={"patches": [p.to_dict() for p in TreeDiff.diff(old, grown)]})
        mirror.apply(revision=2, base_revision=1, kind="patch",
                     payload=add_tx.payload)
        self.assertIsNotNone(_find_in(mirror.snapshot_json(), "appended"))

        remove_tx = RenderTransaction.create(
            revision=3, base_revision=2, kind="patch",
            payload={"patches": [p.to_dict() for p in TreeDiff.diff(grown, new)]})
        mirror.apply(revision=3, base_revision=2, kind="patch",
                     payload=remove_tx.payload)
        snap = mirror.snapshot_json()
        self.assertIsNone(_find_in(snap, "appended"))
        self.assertIsNone(_find_in(snap, "extra"))
        self.assertIsNotNone(_find_in(snap, "title"))


class TestMirrorWidget(unittest.TestCase):
    def test_serialises_the_remote_node_verbatim(self):
        remote = sample_tree()
        widget = MirrorWidget(remote)
        self.assertEqual(widget.to_dict(), remote)

    def test_deep_copies_so_mutations_do_not_leak(self):
        remote = sample_tree()
        widget = MirrorWidget(remote)
        dumped = widget.to_dict()
        dumped["children"][0]["children"][0]["props"]["value"] = "mutated"
        self.assertEqual(widget.to_dict()["children"][0]["children"][0]
                         ["props"]["value"], "Hello")

    def test_binds_forwarding_handlers_for_remote_events(self):
        seen = []

        def on_event(kind, event):
            seen.append((kind, event))

        widget = MirrorWidget(sample_tree(), on_event=on_event)
        button = _find_widget(widget, "btn")
        self.assertIn("click", button.event_handlers)
        button.event_handlers["click"]({"type": "click", "key": "btn",
                                        "data": {}})
        self.assertEqual(seen, [("click", {"type": "click", "key": "btn",
                                           "data": {}})])

    def test_widget_type_matches_remote_type(self):
        widget = MirrorWidget(sample_tree())
        self.assertEqual(widget._widget_type, "Stack")

    def test_key_is_the_remote_key(self):
        widget = MirrorWidget(sample_tree())
        self.assertEqual(widget.key, "_page")


def _find_in(node, key):
    if node is None:
        return None
    if node.get("key") == key:
        return node
    for child in node.get("children") or []:
        found = _find_in(child, key)
        if found is not None:
            return found
    return None


def _find_widget(widget, key):
    for w, _ in widget.walk():
        if w.key == key:
            return w
    return None


if __name__ == "__main__":
    unittest.main()
