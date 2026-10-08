"""
Render transactions, theme sync and window metrics for :class:`App`.

A native ACK is the only operation that advances the confirmed snapshot, so
the desired / confirmed / in-flight UI states stay separate. Split out of
``app.py`` to keep each module focused; the methods run on ``App`` through
:class:`RenderMixin`.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Optional

from pydrud.core.diff import TreeDiff
from pydrud.core.errors import FrameTooLargeError
from pydrud.core.protocol import MAX_FRAME_BYTES, ProtocolError, RenderTransaction
from pydrud.core.state import State
from pydrud.widgets import Widget

MAX_PATCHES = 60

class RenderMixin:
    """Desired-tree diffing, snapshot streaming, theming and metrics."""

    @contextmanager
    def _rendering(self):
        """Mark the render pipeline busy while a frame is prepared and sent.

        ``_render_pending`` only covers a render *queued* behind an in-flight
        frame. Diffing and encoding one takes real time (and hot restart can
        run it off the UI thread), so this is what keeps "the pipeline is
        idle" an honest signal for the test harness and diagnostics (IC-002).
        """
        with self._render_gate:
            self._render_in_progress += 1
        try:
            yield
        finally:
            with self._render_gate:
                self._render_in_progress -= 1

    def update(self):
        """Rebuild and transact the desired tree.

        Python keeps desired, confirmed and in-flight UI state separate. A
        native ACK is the only operation which advances the confirmed snapshot.
        """
        new = self._build_tree()
        self._desired_tree = new
        self._send_desired_tree()

    def _send_desired_tree(self, *, force_snapshot: bool = False) -> None:
        """Send the current desired tree when no render transaction is active.

        The frame is *encoded before it is registered* as in-flight. When a
        frame exceeds :data:`~pydrud.core.protocol.MAX_FRAME_BYTES` the old
        order left a phantom transaction in ``_inflight`` and every later
        render was deferred forever — a silent, permanent UI freeze. Now the
        failure is rolled back, reported loudly, and an oversized snapshot is
        split into a sequence of frames that each fit (see
        :meth:`_plan_snapshot_frames`).

        The call runs inside :meth:`_rendering`, so a consumer that watches
        for an idle pipeline (the test harness, a diagnostics dump) never sees
        "nothing rendering" while a frame is still being prepared (IC-002).
        """
        if not (self._connected and self._transport):
            return
        if self._inflight:
            self._render_pending = True
            if force_snapshot:
                self._render_pending_force_snapshot = True
            return
        force_snapshot = force_snapshot or getattr(self, "_render_pending_force_snapshot", False)
        self._render_pending_force_snapshot = False
        with self._rendering():

            self._render_pending = False
            self._send_desired_tree_now(force_snapshot=force_snapshot)

    def _send_desired_tree_now(self, *, force_snapshot: bool) -> None:
        """Prepare and hand over at most one frame for the current tree."""
        desired = self._desired_tree
        if desired is None:
            return

        base_revision = self._confirmed_revision
        old = self._snapshot

        if not force_snapshot and old is not None:
            try:
                patches = TreeDiff.diff(old, desired)
            except Exception as exc:
                self._report_error(exc)
            else:
                if not patches:
                    return
                patch_payload = {"patches": [p.to_dict() for p in patches]}

                if len(patches) <= MAX_PATCHES or self._fits_frame(patch_payload):
                    if self._send_payload(patch_payload, "patch", base_revision,
                                          snapshot_tree=desired.clone()):
                        return

        snapshot_payload = {"tree": desired.to_dict()}
        if self._send_payload(snapshot_payload, "snapshot", base_revision,
                              snapshot_tree=desired.clone()):
            return
        if self._send_chunked_snapshot(desired, base_revision):
            return

        self._report_error(FrameTooLargeError(
            "render frame exceeds the maximum size of "
            f"{MAX_FRAME_BYTES} bytes even after splitting; a single widget "
            "is too large to send"))

    def _fits_frame(self, payload: dict) -> bool:
        """True when *payload* encodes inside the transport frame limit."""
        return self._try_encode_payload(payload, 1, 0) is not None

    def _try_encode_payload(self, payload: dict, revision: int,
                            base_revision: int) -> Optional[str]:
        """Encode a transaction, returning ``None`` (not raising) when too big."""
        tx = RenderTransaction.create(
            revision=revision, base_revision=base_revision,
            kind=("patch" if "patches" in payload else "snapshot"),
            payload=payload,
        )
        try:
            return self._bridge.encode_transaction(tx)
        except ProtocolError:
            return None

    def _send_payload(self, payload: dict, kind: str, base_revision: int,
                      *, snapshot_tree: Optional[Widget] = None) -> bool:
        """Register and send one render transaction.

        Returns ``False`` (leaving no in-flight state behind) when the frame
        is too large to encode, so the caller can recover.
        """
        revision = max(self._desired_revision, base_revision) + 1
        tx = RenderTransaction.create(
            revision=revision, base_revision=base_revision,
            kind=kind, payload=payload,
        )
        try:
            encoded = self._bridge.encode_transaction(tx)
        except ProtocolError:
            return False
        self._desired_revision = revision
        self._inflight[tx.tx_id] = tx
        self._inflight_trees[tx.tx_id] = snapshot_tree
        self._send(encoded)
        return True

    def _send_chunked_snapshot(self, desired: Widget, base_revision: int) -> bool:
        """Send an oversized tree as a shallow snapshot plus create patches.

        The first frame is a snapshot carrying as much of the tree as fits;
        every omitted subtree is then streamed as ``create`` patches (parents
        before children) in follow-up frames, one per native ACK. The full
        tree becomes the confirmed snapshot once the final frame is acked.
        """
        frames = self._plan_snapshot_frames(desired.to_dict())
        if not frames:
            return False
        payload, kind = frames[0]
        if not self._send_payload(payload, kind, base_revision):
            return False
        self._outbox = list(frames[1:])
        self._outbox_final_tree = desired.clone()
        return True

    def _flush_outbox(self) -> None:
        """Send the next queued chunked-snapshot frame after an ACK."""
        if not self._outbox:
            self._outbox_final_tree = None
            return
        payload, kind = self._outbox.pop(0)
        is_last = not self._outbox
        tree = self._outbox_final_tree if is_last else None
        with self._rendering():
            sent = self._send_payload(payload, kind, self._confirmed_revision,
                                      snapshot_tree=tree)
        if not sent:
            self._outbox.clear()
            self._outbox_final_tree = None
            self._report_error(FrameTooLargeError(
                "a widget subtree is too large to stream over the bridge"))
            return
        if is_last:
            self._outbox_final_tree = None

    def update_widget(self, *widgets: Widget) -> None:
        """Compatibility API: merge explicit widget mutations into the desired tree."""
        if not widgets:
            return self.update()
        if self._current_tree is None:
            return self.update()
        for widget in widgets:
            if not self._replace_widget_reference(self._current_tree, widget.key, widget):
                return self.update()

        self._apply_stylesheets(self._current_tree)
        self._desired_tree = self._current_tree
        self._send_desired_tree()
        return None

    def _replace_widget_reference(self, root: Widget, key: str, replacement: Widget) -> bool:
        stack = [root]
        while stack:
            node = stack.pop()
            for index, child in enumerate(node.children):
                if child.key == key:
                    node.children[index] = replacement
                    return True
                stack.append(child)
        return False

    def render(self):
        """Force a full desired-state snapshot reconciliation."""
        tree = self._build_tree()
        self._desired_tree = tree
        self._send_desired_tree(force_snapshot=True)

    def update_state(self, state: State):
        """Rebuild after a State change."""
        self.update()

    def _send_theme(self) -> None:
        """Hand the current palette to the native renderer.

        Native widgets (ripples, switches, inputs, the status bar) read
        their colours from ``PydrudTheme`` on the Java side; this keeps
        that in step with :class:`pydrud.widgets.theme.Theme`.
        """
        try:
            from pydrud.widgets.theme import Theme as _Theme

            payload = _Theme.payload()

            self._pushed_scheme = getattr(_Theme, "scheme", None)
        except Exception:
            return
        self._send(json.dumps({"cmd": "theme", **payload}) + "\n")

    def _request_system_theme(self) -> None:
        """Fetch optional system palette colours when ``Theme.system()`` opts in."""
        try:
            from pydrud.widgets.theme import Theme as _Theme
            if not _Theme._uses_system() or not self._connected:
                return
            self.invoke("system_colors").then(self._apply_system_theme)
        except Exception as exc:
            self._report_error(exc)

    def _apply_system_theme(self, palette) -> None:
        try:
            from pydrud.widgets.theme import Theme as _Theme
            if _Theme._apply_system_palette(palette):
                self._send_theme()
                self.render()
        except Exception as exc:
            self._report_error(exc)

    def apply_theme(self, *, animate: bool = False,
                    duration: int = 220) -> None:
        """Re-send the palette and repaint after changing :class:`Theme`.

        ::

            Theme.dark()
            app.apply_theme()

        With ``animate=True`` the palette tweens from what the device last
        received to the new one over *duration* milliseconds, so a light/dark
        switch or a re-seed glides instead of snapping.
        """
        from pydrud.widgets.theme import Theme as _Theme
        from pydrud.widgets.theme.colors import ColorScheme as _Scheme

        self._sync_system_theme()
        self._request_system_theme()

        start = getattr(self, "_pushed_scheme", None)
        target = getattr(_Theme, "scheme", None)
        if (not animate or not self._connected or start is None
                or target is None or start is target or duration <= 0):
            self._send_theme()
            self.render()
            return

        frames = max(1, min(20, int(duration / 1000 * 60) or 1))
        interval = (duration / 1000.0) / frames
        state = {"frame": 0}

        token = object()
        self._theme_tween = token

        def _tick() -> None:
            if self._theme_tween is not token:
                return
            state["frame"] += 1
            fraction = state["frame"] / frames
            _Theme.use(_Scheme.lerp(start, target, fraction))
            self._send_theme()
            self.render()
            if state["frame"] < frames:
                self.tasks.after(interval, lambda: self.run_on_ui(_tick))
            else:

                _Theme.use(target)
                self._send_theme()
                self.render()
                self._theme_tween = None

        self.run_on_ui(_tick)

    def _sync_system_theme(self) -> bool:
        """Follow the device's dark-mode setting while the page is on ``system``.

        The renderer reports ``dark`` in its window metrics. When the page is
        in ``"system"`` mode we adopt the matching palette, so PSS ``$token``
        references and Python-resolved colours flip together instead of the
        Python side staying light while the native side goes dark.

        A page that opted into the device's wallpaper palette via
        :meth:`Theme.system` is left alone: that palette is authoritative.

        :returns: True when the palette changed.
        """
        from pydrud.core.responsive import MediaQuery as _MQ
        from pydrud.widgets.theme import Theme as _Theme

        if getattr(self._page, "theme_mode", "light") != "system":
            return False
        if _Theme._uses_system():
            return False
        want_dark = bool(_MQ.is_dark())
        if want_dark == bool(_Theme.dark_mode):
            return False
        if want_dark:
            _Theme.dark()
        else:
            _Theme.light()
        self._send_theme()
        return True

    def _handle_render_confirmation(self, event_type: str, data: dict) -> None:
        tx_id = str(data.get("transaction_id", ""))
        tx = self._inflight.pop(tx_id, None)
        sent_tree = self._inflight_trees.pop(tx_id, None)
        if tx is None:
            return
        revision = int(data.get("revision", 0) or 0)
        if revision != tx.revision:
            self._report_error(RuntimeError(
                f"Render confirmation mismatch for {tx_id}: "
                f"expected {tx.revision}, got {revision}"
            ))
            return
        if event_type == "render_ack":
            self._confirmed_revision = revision
            if sent_tree is not None:
                self._snapshot = sent_tree.clone()

            if self._outbox:
                self._flush_outbox()
                return
            if self._render_pending:

                self._send_desired_tree()
            return

        self._confirmed_revision = int(data.get("native_revision", 0) or 0)
        if self._desired_tree is None or not (self._connected and self._transport):
            return

        self._outbox.clear()
        self._outbox_final_tree = None
        desired = self._desired_tree
        with self._rendering():
            payload = {"tree": desired.to_dict()}
            if self._send_payload(payload, "snapshot", self._confirmed_revision,
                                  snapshot_tree=desired.clone()):
                return
            if self._send_chunked_snapshot(desired, self._confirmed_revision):
                return
        self._report_error(FrameTooLargeError(
            "render recovery frame exceeds the maximum size of "
            f"{MAX_FRAME_BYTES} bytes"))

    def _handle_ready(self, d: dict) -> None:
        """First contact: negotiate native capabilities, then render."""
        advertised = d.get("capabilities")
        negotiated = dict(advertised) if isinstance(advertised, dict) else {}
        if negotiated != self._native_capabilities:

            self._elements.clear()
        self._native_capabilities = negotiated

        self.render()
        self._apply_metrics(d)

        self._sync_system_theme()

        self._send(json.dumps({"cmd": "theme_mode",
                               "mode": getattr(self._page, "theme_mode",
                                               "system")}) + "\n")
        self.render()

    def _handle_metrics(self, d: dict) -> None:
        """The window changed (rotation, resize, insets, font scale).

        Only re-render when something actually moved, so a stream of
        identical inset callbacks does not thrash the view tree.
        """
        if not self._apply_metrics(d):
            return
        self._sync_system_theme()
        for cb in list(self._metrics_handlers):
            try:
                cb(_MQ_INFO())
            except Exception as exc:
                self._report_error(exc)
        self.render()

    def _apply_metrics(self, d: dict) -> bool:
        """Feed a ``ready``/``metrics`` payload into MediaQuery + Responsive."""
        from pydrud.core.responsive import MediaQuery as _MQ

        payload = {k: v for k, v in dict(d or {}).items() if v is not None}
        payload.setdefault("width", 360)
        payload.setdefault("height", 640)
        payload.setdefault("density", 2.0)
        try:
            return _MQ.update(**payload)
        except Exception as exc:
            self._report_error(exc)
            return False

    def on_metrics_change(self, callback):
        """Run *callback(ScreenInfo)* whenever the window size changes.

        ::

            @app.on_metrics_change
            def _(info):
                print(info.width, info.orientation, info.breakpoint)
        """
        if not callable(callback):
            raise TypeError("on_metrics_change() expects a callable")
        self._metrics_handlers.append(callback)
        return callback

def _MQ_INFO():
    from pydrud.core.responsive import MediaQuery as _MQ

    return _MQ.info()
