"""Forms — a realistic signup flow with live validation."""

from __future__ import annotations

from pydrud import (
    Button, Card, Checkbox, Column, Divider, EmailField, Form, FormField,
    Icon, Icons, PasswordField, Spacing, Text, TextField, Theme, Widget,
    custom, email as email_validator, min_length, required,
)

from app.runtime import refresh
from app.state import State

__all__ = ["DEMO"]

submitted = State(False, name="pg_form_done")
values = State({}, name="pg_form_values")
accepted = State(False, name="pg_form_terms")


def _submit(data: dict):
    values.value = dict(data)
    submitted.value = True
    refresh()


def _reset(_event):
    submitted.value = False
    values.value = {}
    accepted.value = False
    refresh()


def _accept(event):
    accepted.value = bool(event.get("value", False))
    refresh()


def _is_pydrud_fan(value) -> bool:
    return True  # everyone is; the custom validator just needs a predicate


def build(key: str) -> Widget:
    if submitted.value:
        return Card(
            key=f"{key}_done",
            padding=Spacing.XL,
            child=Column(
                key=f"{key}_done_col",
                spacing=Spacing.MD,
                horizontal_alignment="center",
                children=[
                    Icon(Icons.CHECK_CIRCLE, key=f"{key}_done_icon", size=44,
                         color=Theme.primary),
                    Text("Account created", key=f"{key}_done_title", size=18,
                         weight=700, color=Theme.text),
                    Text("Values captured by Form.submit():",
                         key=f"{key}_done_sub", size=12,
                         color=Theme.text_secondary),
                    Column(
                        key=f"{key}_done_rows",
                        spacing=Spacing.XS,
                        children=[
                            Text(f"{name}: {value}",
                                 key=f"{key}_done_row{i}", size=12,
                                 color=Theme.text)
                            for i, (name, value) in enumerate(
                                values.value.items())
                        ],
                    ),
                    Button("Start over", key=f"{key}_again",
                           variant="tonal", icon=Icons.REFRESH
                           ).on_click(_reset),
                ],
            ),
        )

    form = Form(
        FormField("name",
                  TextField("", key=f"{key}_name", label="Display name",
                            hint="ada@example.dev"),
                  label="Display name",
                  validators=[required("Pick a name other developers see")]),
        FormField("email",
                  EmailField("", key=f"{key}_email", label="Email"),
                  label="Email", validators=[required(), email_validator()]),
        FormField("password",
                  PasswordField("", key=f"{key}_password", label="Password"),
                  label="Password",
                  validators=[required(), min_length(8)],
                  helper="At least 8 characters"),
        FormField("bio",
                  TextField("", key=f"{key}_bio", label="Bio",
                            multiline=True, max_lines=3),
                  label="Bio (optional)",
                  validators=[custom(_is_pydrud_fan)]),
        on_submit=_submit,
        key=f"{key}_form",
    )
    return Column(
        key=f"{key}_col",
        spacing=Spacing.LG,
        children=[
            Card(
                key=f"{key}_card",
                padding=Spacing.LG,
                child=Column(
                    key=f"{key}_card_col",
                    spacing=Spacing.MD,
                    children=[
                        Text("Join the preview", key=f"{key}_title", size=16,
                             weight=700, color=Theme.text),
                        Text("Errors appear on submit, then clear field "
                             "by field as you fix them.",
                             key=f"{key}_sub", size=12,
                             color=Theme.text_secondary),
                        Divider(key=f"{key}_div"),
                        form,
                        Checkbox("I accept the demo terms",
                                 key=f"{key}_terms",
                                 checked=accepted.value).on_change(_accept),
                    ],
                ),
            ),
            Button("Create account", key=f"{key}_submit", full_width=True,
                   icon=Icons.ROCKET, disabled=not accepted.value
                   ).on_click(lambda _e: form.submit()),
        ],
    )


from app.data.playground import PlaygroundDemo  # noqa: E402

DEMO = PlaygroundDemo(
    id="forms",
    title="Forms & Validation",
    blurb="A signup flow with live, per-field validation.",
    icon="verified",
    tags=("form", "validate", "submit"),
    build=build,
)
