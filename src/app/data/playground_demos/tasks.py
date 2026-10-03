"""Task board — list mutations, filtering, reordering and dismissal."""

from __future__ import annotations

from pydrud import (
    Button, Card, Checkbox, Colors, Column, Container, Dismissible, Icon,
    Icons, Radius, Row, SegmentedButton, Spacing, Text, TextField, Theme,
    Widget,
)
from pydrud import ReorderableList

from app.runtime import refresh
from app.state import State
from app.theme import pad

__all__ = ["DEMO"]

tasks = State((
    {"id": 1, "title": "Run pydrud dev", "done": True},
    {"id": 2, "title": "Scan the QR code", "done": True},
    {"id": 3, "title": "Edit a screen", "done": False},
    {"id": 4, "title": "Watch the patch land", "done": False},
    {"id": 5, "title": "Ship without rebuilding", "done": False},
), name="pg_tasks")
draft = State("", name="pg_task_draft")
filter_mode = State(0, name="pg_task_filter")
next_id = State(6, name="pg_task_next")


def _add(_event=None):
    title = draft.value.strip()
    if not title:
        return
    tasks.value = tasks.value + ({"id": next_id.value, "title": title,
                                  "done": False},)
    next_id.value += 1
    draft.value = ""
    refresh()


def _set_draft(event):
    draft.value = str(event.get("value", ""))
    refresh()


def _toggle(task_id: int):
    def handler(event):
        updated = tuple(
            {**t, "done": bool(event.get("value", t["done"]))}
            if t["id"] == task_id else t
            for t in tasks.value)
        tasks.value = updated
        refresh()
    return handler


def _remove(task_id: int):
    def handler(_event):
        tasks.value = tuple(t for t in tasks.value if t["id"] != task_id)
        refresh()
    return handler


def _reorder(event):
    data = event.data if hasattr(event, "data") else {}
    source = int(data.get("from", -1))
    target = int(data.get("to", -1))
    if source < 0 or target < 0:
        return
    items = list(tasks.value)
    items.insert(target, items.pop(source))
    tasks.value = tuple(items)
    refresh()


def _set_filter(event):
    try:
        filter_mode.value = int(event.get("value", filter_mode.value))
    except (TypeError, ValueError):
        return
    refresh()


def _clear_done(_event):
    tasks.value = tuple(t for t in tasks.value if not t["done"])
    refresh()


def build(key: str) -> Widget:
    mode = filter_mode.value
    visible = [t for t in tasks.value
               if mode == 0 or (mode == 1 and not t["done"])
               or (mode == 2 and t["done"])]
    done_count = sum(1 for t in tasks.value if t["done"])

    composer = Row(
        key=f"{key}_composer",
        spacing=Spacing.SM,
        vertical_alignment="center",
        children=[
            TextField(draft.value, key=f"{key}_draft",
                      hint="Add a task…", expand=1).on_change(_set_draft),
            Button("", key=f"{key}_add", icon=Icons.ADD,
                   size="md").on_click(_add),
        ],
    )

    if not visible:
        board = Container(
            key=f"{key}_empty",
            width="match",
            padding=Spacing.XL,
            border_radius=Radius.MD,
            bg=Theme.surface_variant,
            child=Column(
                key=f"{key}_empty_col",
                spacing=Spacing.XS,
                horizontal_alignment="center",
                children=[
                    Icon(Icons.CHECK_CIRCLE, key=f"{key}_empty_icon",
                         size=32, color=Theme.primary),
                    Text("Nothing here", key=f"{key}_empty_title", size=14,
                         weight=600, color=Theme.text),
                    Text("Add a task or switch the filter.",
                         key=f"{key}_empty_sub", size=12,
                         color=Theme.text_secondary),
                ],
            ),
        )
    else:
        rows = []
        for index, task in enumerate(visible):
            rows.append(Dismissible(
                key=f"{key}_item{task['id']}",
                child=Container(
                    key=f"{key}_tile{task['id']}",
                    width="match",
                    padding=pad(horizontal=Spacing.SM, vertical=Spacing.XS),
                    bg=Theme.surface,
                    child=Row(
                        key=f"{key}_row{task['id']}",
                        spacing=Spacing.SM,
                        vertical_alignment="center",
                        children=[
                            Checkbox(task["title"],
                                     key=f"{key}_check{task['id']}",
                                     checked=task["done"]
                                     ).on_change(_toggle(task["id"])),
                        ],
                    ),
                ),
                direction="end",
                background=Colors.ERROR,
                icon=Icons.DELETE,
                on_dismiss=_remove(task["id"]),
            ))
        board = ReorderableList(
            rows,
            key=f"{key}_board",
            spacing=Spacing.SM,
            on_reorder=_reorder,
        )

    return Column(
        key=f"{key}_col",
        spacing=Spacing.LG,
        children=[
            Card(
                key=f"{key}_hero",
                padding=Spacing.LG,
                child=Column(
                    key=f"{key}_hero_col",
                    spacing=Spacing.MD,
                    children=[
                        Row(
                            key=f"{key}_hero_row",
                            spacing=Spacing.MD,
                            vertical_alignment="center",
                            children=[
                                Icon(Icons.AGENDA, key=f"{key}_hero_icon",
                                     size=22, color=Theme.primary),
                                Text(f"{done_count} of {len(tasks.value)} "
                                     "done", key=f"{key}_hero_label",
                                     size=14, weight=600,
                                     color=Theme.text, expand=1),
                                Button("Clear done", key=f"{key}_clear",
                                       variant="text", size="sm",
                                       icon=Icons.DELETE
                                       ).on_click(_clear_done),
                            ],
                        ),
                        SegmentedButton(
                            ["All", "Open", "Completed"],
                            key=f"{key}_filter",
                            selected=filter_mode.value
                        ).on_change(_set_filter),
                        composer,
                    ],
                ),
            ),
            board,
            Text("Long-press a row to drag it into a new order; swipe it "
                 "right to delete. Both feed straight back into State.",
                 key=f"{key}_note", size=12,
                 color=Theme.text_secondary, text_align="center"),
        ],
    )


from app.data.playground import PlaygroundDemo  # noqa: E402

DEMO = PlaygroundDemo(
    id="tasks",
    title="Task Board",
    blurb="Add, complete, filter, reorder and dismiss — lists that mutate.",
    icon="agenda",
    tags=("list", "reorder", "dismissible", "state"),
    build=build,
)
