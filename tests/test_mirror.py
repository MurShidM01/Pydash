"""The mirrored remote tree and its patch applier.

These tests pin the two properties the whole preview rests on: patches are
applied with exactly the host's semantics (and rejected when stale), and a
:class:`~app.preview.mirror.MirrorWidget` serialises back to the *same* JSON
the server sent — which is what makes the local diff engine emit the same
patches a full APK build would have.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from app.preview.mirror import (  # noqa: E402
    MirrorApplyError,
    MirrorWidget,
    RemoteTree,
    mirror_key,
    remote_key,
)


def _node(key, value="", type_="Text", children=None):
    return {
        "type": type_,
        "key": key,
        "style": {},
        "props": {"value": value},
        "children": children or [],
    }


def _root():
    return {
        "type": "Column",
        "key": "root",
        "style": {"padding": {"left": 4}},
        "props": {},
        "children": [_node("a", "A"), _node("b", "B")],
    }


def _snapshot(tree, revision=1):
    return dict(revision=revision, base_revision=0, kind="snapshot",
                payload={"tree": tree})


def _patch(revision, base_revision, *ops):
    return dict(revision=revision, base_revision=base_revision, kind="patch",
                payload={"patches": list(ops)})


def _keys(tree):
    return [child["key"] for child in tree["children"]]


class TestRemoteTree(unittest.TestCase):
    def setUp(self):
        self.tree = RemoteTree()

    def test_a_snapshot_becomes_the_root(self):
        self.assertTrue(self.tree.is_empty)
        self.tree.apply(**_snapshot(_root()))
        self.assertFalse(self.tree.is_empty)
        self.assertEqual(self.tree.revision, 1)
        self.assertEqual(self.tree.node_count(), 3)
        self.assertEqual(self.tree.snapshot_json()["key"], "root")

    def test_snapshot_json_is_a_copy(self):
        self.tree.apply(**_snapshot(_root()))
        copy = self.tree.snapshot_json()
        copy["children"].clear()
        self.assertEqual(self.tree.node_count(), 3)

    def test_create_inserts_at_the_given_index(self):
        self.tree.apply(**_snapshot(_root()))
        self.tree.apply(**_patch(2, 1, {
            "op": "create", "key": "c", "parent_key": "root", "index": 1,
            "tree": _node("c", "C"),
        }))
        self.assertEqual(_keys(self.tree.snapshot_json()), ["a", "c", "b"])
        self.assertEqual(self.tree.revision, 2)

    def test_delete_removes_a_child(self):
        self.tree.apply(**_snapshot(_root()))
        self.tree.apply(**_patch(2, 1, {
            "op": "delete", "key": "a", "parent_key": "root",
        }))
        self.assertEqual(_keys(self.tree.snapshot_json()), ["b"])

    def test_move_reorders_a_child(self):
        self.tree.apply(**_snapshot(_root()))
        self.tree.apply(**_patch(2, 1, {
            "op": "move", "key": "b", "parent_key": "root", "index": 0,
        }))
        self.assertEqual(_keys(self.tree.snapshot_json()), ["b", "a"])

    def test_replace_swaps_a_child(self):
        self.tree.apply(**_snapshot(_root()))
        self.tree.apply(**_patch(2, 1, {
            "op": "replace", "key": "b", "parent_key": "root",
            "tree": _node("b", "B2"),
        }))
        root = self.tree.snapshot_json()
        values = {c["key"]: c["props"]["value"] for c in root["children"]}
        self.assertEqual(values["b"], "B2")

    def test_update_merges_props_and_style(self):
        self.tree.apply(**_snapshot(_root()))
        self.tree.apply(**_patch(2, 1, {
            "op": "update", "key": "a",
            "props": {"value": "A2", "_visible": False},
            "style": {"color": "#FF000000", "opacity": None},
        }))
        node = self.tree.snapshot_json()["children"][0]
        self.assertEqual(node["props"]["value"], "A2")
        self.assertFalse(node["visible"])
        self.assertEqual(node["style"]["color"], "#FF000000")
        self.assertNotIn("opacity", node["style"])

    def test_update_maps_meta_keys_to_node_metadata(self):
        self.tree.apply(**_snapshot(_root()))
        self.tree.apply(**_patch(2, 1, {
            "op": "update", "key": "a",
            "props": {"_events": ["click"], "_has_events": True,
                      "_expand": 2, "_tooltip": "hi"},
        }))
        node = self.tree.snapshot_json()["children"][0]
        self.assertEqual(node["events"], ["click"])
        self.assertTrue(node["has_events"])
        self.assertEqual(node["expand"], 2)
        self.assertEqual(node["tooltip"], "hi")

    def test_a_stale_patch_is_rejected(self):
        self.tree.apply(**_snapshot(_root()))
        with self.assertRaises(MirrorApplyError) as ctx:
            self.tree.apply(**_patch(9, 7, {
                "op": "delete", "key": "a", "parent_key": "root",
            }))
        self.assertIn("stale_base", str(ctx.exception))
        # The tree is untouched.
        self.assertEqual(self.tree.revision, 1)
        self.assertEqual(_keys(self.tree.snapshot_json()), ["a", "b"])

    def test_an_unknown_op_is_rejected(self):
        self.tree.apply(**_snapshot(_root()))
        with self.assertRaises(MirrorApplyError):
            self.tree.apply(**_patch(2, 1, {"op": "frobnicate", "key": "a"}))

    def test_a_root_level_replace_swaps_the_whole_tree(self):
        self.tree.apply(**_snapshot(_root()))
        self.tree.apply(**_patch(2, 1, {
            "op": "replace", "key": "root", "parent_key": "",
            "tree": _node("root", type_="Scaffold", children=[_node("z", "Z")]),
        }))
        root = self.tree.snapshot_json()
        self.assertEqual(root["type"], "Scaffold")
        self.assertEqual(_keys(root), ["z"])

    def test_reset_empties_the_tree(self):
        self.tree.apply(**_snapshot(_root()))
        self.tree.reset()
        self.assertTrue(self.tree.is_empty)
        self.assertEqual(self.tree.revision, 0)


class TestMirrorWidget(unittest.TestCase):
    def test_re_emits_the_remote_node_verbatim(self):
        node = {
            "type": "Button", "key": "save",
            "style": {"bg": "#FF112233", "padding": 12},
            "props": {"text": "Save", "variant": "filled"},
            "events": ["click"],
            "expand": 1,
            "children": [],
        }
        widget = MirrorWidget(node, on_event=lambda *a: None)
        out = widget.to_dict()
        self.assertEqual(out["type"], "Button")
        self.assertEqual(remote_key(out["key"]), "save")
        self.assertEqual(out["style"], {"bg": "#FF112233", "padding": 12})
        self.assertEqual(out["props"], {"text": "Save", "variant": "filled"})
        self.assertEqual(out["expand"], 1)
        self.assertTrue(out["has_events"])
        self.assertEqual(out["events"], ["click"])

    def test_remote_keys_are_namespaced_and_round_trip(self):
        widget = MirrorWidget(_node("_page"), on_event=lambda *a: None)
        # A project's page root is `_page` — the same framework key as
        # Pydash's own root — so the mirror must re-key it out of the way.
        self.assertNotEqual(widget.key, "_page")
        self.assertEqual(widget.key, mirror_key("_page"))
        self.assertEqual(widget.remote_key(), "_page")
        self.assertEqual(remote_key(widget.key), "_page")

    def test_children_are_rebuilt_recursively(self):
        node = _root()
        widget = MirrorWidget(node, on_event=lambda *a: None)
        self.assertEqual(len(widget.children), 2)
        self.assertEqual(widget.children[0].remote_key(), "a")

    def test_events_are_bound_and_forwarded(self):
        seen = []
        node = _node("btn", type_="Button")
        node["events"] = ["click", "long_press"]
        widget = MirrorWidget(node, on_event=lambda name, event: seen.append(name))

        class _Event:
            key = "btn"
            value = None

        widget.event_handlers["click"](_Event())
        self.assertEqual(seen, ["click"])

    def test_a_page_rooted_remote_tree_does_not_collide_with_the_host(self):
        from pydrud import Column

        remote = {
            "type": "Column", "key": "_page", "style": {}, "props": {},
            "children": [{
                "type": "Text", "key": "_page._body", "style": {},
                "props": {"value": "Hello"}, "children": [],
            }],
        }
        # The host tree already owns `_page` (Pydrud's page root); mirroring a
        # project whose root is also `_page` used to raise
        # "Duplicate Pydrud widget key '_page'" and blank the preview.
        host = Column(key="pd_stage", children=[
            Column(key="_page", children=[]),
            MirrorWidget(remote, on_event=lambda *a: None),
        ])
        self.assertEqual(host.to_dict()["key"], "pd_stage")

    def test_a_malformed_node_is_rejected(self):
        with self.assertRaises(MirrorApplyError):
            MirrorWidget({"key": "x"}, on_event=lambda *a: None)
        with self.assertRaises(MirrorApplyError):
            MirrorWidget({"type": "Text"}, on_event=lambda *a: None)


if __name__ == "__main__":
    unittest.main()
