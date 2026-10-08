"""The mirrored remote widget tree and its patch applier.

The development server sends the *serialised* widget tree of the project being
developed (the same JSON the generated Android renderer consumes) plus
incremental patches as the developer edits Python. Pydash keeps that JSON as
its source of truth — :class:`RemoteTree` — and rehydrates it into
:class:`MirrorWidget` nodes for the local render pipeline.

Because :class:`MirrorWidget` serialises back to *exactly* the JSON the server
sent (same ``type``, ``key``, ``style``, ``props``, ``events``), Pydash's own
diff engine produces the same minimal view patches a full APK build would have
applied — the preview is rendered by the real renderer, not a re-implementation.

Patch semantics mirror ``pydrud.core.diff`` (``create``/``update``/``delete``/
``move``/``replace``) and the native ``ViewFactory.applyPatch`` that consumes
them.
"""

from __future__ import annotations

import copy
import threading
from typing import Any, Callable, Optional

from pydrud import Widget

__all__ = [
    "MirrorApplyError", "MirrorWidget", "RemoteTree", "mirror_key", "remote_key",
]

#: Every mirrored node is re-keyed into this namespace before it enters the
#: local widget tree. The remote project is an ordinary Pydrud app, so its tree
#: carries framework keys — the page root ``_page``, a Scaffold's ``_body`` /
#: ``_stack`` and friends — that would collide with Pydash's own page root and
#: shell internals and make ``validate_tree_keys`` reject the tree. Prefixing
#: keeps the two key spaces disjoint while leaving the ``RemoteTree`` (which
#: the dev server patches by its own keys) untouched.
_REMOTE_PREFIX = "pdremote_"


def mirror_key(key: str) -> str:
    """The collision-free local key for a remote node key."""
    return _REMOTE_PREFIX + str(key or "")


def remote_key(local_key: str) -> str:
    """The dev project's key behind a mirrored (prefixed) local key."""
    text = str(local_key or "")
    return text[len(_REMOTE_PREFIX):] if text.startswith(_REMOTE_PREFIX) else text


class MirrorApplyError(RuntimeError):
    """A remote patch could not be applied to the mirrored tree.

    Carries the current revision so the client can NACK with it and the
    server's recovery snapshot can resynchronise.
    """

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = str(reason)


class MirrorWidget(Widget):
    """A live Widget wrapping one node of the remote tree.

    * ``key`` is the remote key *namespaced* by :func:`mirror_key`, so it can
      never collide with Pydash's own keys; :meth:`remote_key` recovers the
      key the dev server dispatches events and patches by;
    * ``_widget_type`` matches the remote type so the local diff engine
      produces ``update`` patches instead of replacing the view;
    * every remote event name is bound to a forwarding handler;
    * :meth:`_serialise_self` re-emits the remote node verbatim.
    """

    def __init__(self, node: dict, *, on_event: Optional[Callable] = None):
        node = _validated_node(node)
        self._node = node
        self._on_event = on_event
        self._remote_key = str(node.get("key") or "")
        super().__init__(key=mirror_key(self._remote_key))
        self._widget_type = str(node.get("type") or "Widget")
        self._auto_key = False
        self.style = dict(node.get("style") or {})
        self.expand = node.get("expand")
        self.visible = node.get("visible", True)
        self.tooltip = node.get("tooltip")
        self.semantics = node.get("semantics")
        for name in (node.get("events") or []):
            name = str(name)
            if on_event is not None:
                self.event_handlers[name] = (
                    lambda event, _name=name: on_event(_name, event))
        self.children = [MirrorWidget(child, on_event=on_event)
                         for child in (node.get("children") or [])]

    # ── serialisation ─────────────────────────────────────────────────────

    def _serialise_props(self) -> dict:
        return copy.deepcopy(self._node.get("props") or {})

    def _serialise_self(self) -> dict:
        """The remote node exactly as the server sent it (children filled in)."""
        node = self._node
        return {
            "type": str(node.get("type") or "Widget"),
            "key": self.key,
            "style": copy.deepcopy(node.get("style") or {}),
            "expand": node.get("expand"),
            "visible": node.get("visible", True),
            "tooltip": node.get("tooltip"),
            "semantics": node.get("semantics"),
            "has_events": bool(self.event_handlers),
            "events": (sorted(self.event_handlers.keys())
                       or list(node.get("events") or [])),
            "props": copy.deepcopy(node.get("props") or {}),
            "children": [],
        }

    def remote_key(self) -> str:
        """The dev server's key for this node (without the local prefix)."""
        return self._remote_key


def _validated_node(node: Any) -> dict:
    if not isinstance(node, dict):
        raise MirrorApplyError("remote tree node is not an object")
    if not node.get("type"):
        raise MirrorApplyError("remote tree node is missing its type")
    if not node.get("key"):
        raise MirrorApplyError("remote tree node is missing its key")
    return node


#: ``update`` prop keys the renderer treats as node metadata, not widget props.
_META_KEYS = {
    "_events": "events",
    "_has_events": "has_events",
    "_expand": "expand",
    "_visible": "visible",
    "_tooltip": "tooltip",
    "_semantics": "semantics",
}


class RemoteTree:
    """Thread-safe mirror of the remote page, updated by render transactions.

    The reader thread of the socket client applies snapshots and patches here;
    the UI thread reads :meth:`snapshot_json` when rebuilding the preview
    screen. A lock keeps the two from interleaving.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._root: Optional[dict] = None
        self.revision = 0

    # ── queries ───────────────────────────────────────────────────────────

    @property
    def is_empty(self) -> bool:
        with self._lock:
            return self._root is None

    def snapshot_json(self) -> Optional[dict]:
        """A deep copy of the current tree (safe to build widgets from)."""
        with self._lock:
            return copy.deepcopy(self._root)

    def node_count(self) -> int:
        with self._lock:
            return _count(self._root)

    # ── transaction application ───────────────────────────────────────────

    def apply(self, *, revision: int, base_revision: int, kind: str,
              payload: dict) -> int:
        """Apply one render transaction; returns the number of patch ops.

        Raises :class:`MirrorApplyError` when the transaction cannot be
        applied; the caller should then NACK so the server resends a full
        snapshot.
        """
        with self._lock:
            if kind == "snapshot":
                tree = payload.get("tree")
                _validated_node(tree)
                self._root = copy.deepcopy(tree)
                self.revision = int(revision)
                return 1
            if kind == "patch":
                if int(base_revision) != self.revision:
                    raise MirrorApplyError(
                        f"stale_base_revision: patch expects {base_revision}, "
                        f"mirror is at {self.revision}")
                patches = payload.get("patches")
                if not isinstance(patches, list):
                    raise MirrorApplyError("patch transaction without patches")
                for patch in patches:
                    self._apply_patch(patch if isinstance(patch, dict) else {})
                self.revision = int(revision)
                return len(patches)
            raise MirrorApplyError(f"unknown transaction kind {kind!r}")

    def reset(self) -> None:
        with self._lock:
            self._root = None
            self.revision = 0

    # ── patch operations ──────────────────────────────────────────────────

    def _apply_patch(self, patch: dict) -> None:
        op = str(patch.get("op") or "")
        key = str(patch.get("key") or "")
        parent_key = str(patch.get("parent_key") or "")
        index = int(patch.get("index", -1))

        if op == "create":
            tree = copy.deepcopy(_validated_node(patch.get("tree")))
            if parent_key == "":
                # The virtual root container only ever holds one child.
                self._root = tree
                return
            children = self._children_of(parent_key, key)
            children.insert(_clamp_index(len(children), index,
                                         len(children) + 1), tree)
            return

        if op == "delete":
            if parent_key == "":
                if self._root and self._root.get("key") == key:
                    self._root = None
                    return
                raise MirrorApplyError(f"delete: unknown root key {key!r}")
            if not self._remove_child(parent_key, key):
                raise MirrorApplyError(f"delete: unknown key {key!r}")
            return

        if op == "move":
            if parent_key == "":
                return  # a single-element container cannot be reordered
            node = self._find(key)
            if node is None:
                raise MirrorApplyError(f"move: unknown key {key!r}")
            self._remove_child(parent_key, key)
            children = self._children_of(parent_key, key)
            children.insert(_clamp_index(len(children), index,
                                         len(children) + 1), node)
            return

        if op == "replace":
            tree = copy.deepcopy(_validated_node(patch.get("tree")))
            if parent_key == "":
                if self._root is None or self._root.get("key") == key:
                    self._root = tree
                    return
                raise MirrorApplyError(f"replace: unknown root key {key!r}")
            children = self._children_of(parent_key, key)
            position = _find_index(children, key)
            if position < 0:
                position = _clamp_index(len(children), index, len(children))
            children[position] = tree
            return

        if op == "update":
            node = self._find(key)
            if node is None:
                raise MirrorApplyError(f"update: unknown key {key!r}")
            self._apply_update(node, patch)
            return

        raise MirrorApplyError(f"unknown patch op {op!r}")

    @staticmethod
    def _apply_update(node: dict, patch: dict) -> None:
        props = patch.get("props")
        if isinstance(props, dict):
            target = node.setdefault("props", {})
            for name, value in props.items():
                meta = _META_KEYS.get(name)
                if meta is not None:
                    node[meta] = value
                else:
                    target[name] = value
        style = patch.get("style")
        if isinstance(style, dict):
            target = node.setdefault("style", {})
            for name, value in style.items():
                if value is None:
                    target.pop(name, None)
                else:
                    target[name] = value

    # ── tree walking ──────────────────────────────────────────────────────

    def _find(self, key: str) -> Optional[dict]:
        if self._root is None:
            return None
        if self._root.get("key") == key:
            return self._root
        return _find_child(self._root.get("children") or [], key)

    def _children_of(self, parent_key: str, key: str) -> list:
        """The children list of *parent_key* (the patch's target slot)."""
        if self._root is not None and parent_key == self._root.get("key"):
            return self._root.setdefault("children", [])
        parent = self._find(parent_key)
        if parent is None:
            raise MirrorApplyError(
                f"parent {parent_key!r} not found for {key!r}")
        return parent.setdefault("children", [])

    def _remove_child(self, parent_key: str, key: str) -> bool:
        children = self._children_of(parent_key, key)
        index = _find_index(children, key)
        if index < 0:
            return False
        children.pop(index)
        return True


def _find_child(children: list, key: str) -> Optional[dict]:
    for child in children:
        if child.get("key") == key:
            return child
        found = _find_child(child.get("children") or [], key)
        if found is not None:
            return found
    return None


def _find_index(children: list, key: str) -> int:
    for index, child in enumerate(children):
        if child.get("key") == key:
            return index
    return -1


def _clamp_index(fallback: int, index: int, limit: int) -> int:
    if index is None or index < 0:
        index = fallback if fallback >= 0 else 0
    return max(0, min(index, max(0, limit - 1)))


def _count(node: Optional[dict]) -> int:
    if node is None:
        return 0
    return 1 + sum(_count(child) for child in (node.get("children") or []))
