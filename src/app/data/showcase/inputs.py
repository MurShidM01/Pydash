"""Input & form demos — text fields, selections, sliders and validation."""

from __future__ import annotations

from pydrud import (
    Button, Checkbox, Column, Divider, Dropdown, EmailField, Form, FormField,
    NumberField, PasswordField, PhoneField, Radio, Rating, SearchField,
    SegmentedButton, Slider, Spacing, Switch, Text, TextField, Theme,
    UrlField, Widget, between, email as email_validator, min_length,
    required, url as url_validator,
)

from app.runtime import refresh
from app.state import State

__all__ = ["CATEGORY"]

#: Shared interactive state for the input demos.
name = State("", name="input_name")
volume = State(40.0, name="input_volume")
enabled = State(True, name="input_enabled")
subscribe = State(False, name="input_subscribe")
flavour = State("Matcha", name="input_flavour")
rating = State(3.5, name="input_rating")
segment = State(0, name="input_segment")
form_note = State("", name="form_note")

FLAVOURS = ("Matcha", "Espresso", "Chai", "Cocoa", "Yuzu")


def _field_kinds(key: str) -> Widget:
    return Column(
        key=f"{key}_col",
        spacing=Spacing.MD,
        children=[
            TextField(name.value, key=f"{key}_plain", hint="Plain filled field",
                      label="Name").on_change(_set_name),
            TextField("", key=f"{key}_outlined", hint="Outlined variant",
                      variant="outlined"),
            SearchField("", key=f"{key}_search", hint="SearchField preset"),
            EmailField("", key=f"{key}_email", hint="Email keyboard"),
            PasswordField("", key=f"{key}_password", hint="Obscured input"),
            NumberField("0", key=f"{key}_number", hint="Numeric keyboard"),
            PhoneField("", key=f"{key}_phone", hint="Phone keyboard"),
            UrlField("", key=f"{key}_url", hint="URL keyboard"),
            TextField("", key=f"{key}_multiline", hint="Multiline (3 lines)",
                      multiline=True, max_lines=3),
        ],
    )


def _set_name(event):
    name.value = str(event.get("value", ""))
    refresh()


def _selections(key: str) -> Widget:
    return Column(
        key=f"{key}_col",
        spacing=Spacing.MD,
        children=[
            Dropdown(FLAVOURS, value=flavour.value, key=f"{key}_dropdown",
                     hint="Pick a flavour").on_change(_set_flavour),
            Column(
                key=f"{key}_radios",
                spacing=Spacing.XS,
                children=[
                    Radio(f, key=f"{key}_radio{i}", group="flavour",
                          selected=flavour.value == f
                          ).on_change(lambda e, value=f: _pick(value))
                    for i, f in enumerate(FLAVOURS[:3])
                ],
            ),
            Checkbox("I agree to the demo licence", key=f"{key}_check",
                     checked=subscribe.value).on_change(_set_subscribe),
            Switch("Live inputs", active=enabled.value,
                   key=f"{key}_switch").on_change(_set_enabled),
            Rating(rating.value, key=f"{key}_rating", count=5, half=True
                   ).on_change(_set_rating),
        ],
    )


def _set_flavour(event):
    flavour.value = str(event.get("value", flavour.value))
    refresh()


def _pick(value: str):
    flavour.value = value
    refresh()


def _set_subscribe(event):
    subscribe.value = bool(event.get("value", False))
    refresh()


def _set_enabled(event):
    enabled.value = bool(event.get("value", False))
    refresh()


def _set_rating(event):
    try:
        rating.value = float(event.get("value", rating.value))
    except (TypeError, ValueError):
        return
    refresh()


def _slider_progress(key: str) -> Widget:
    from pydrud import ProgressBar

    return Column(
        key=f"{key}_col",
        spacing=Spacing.MD,
        children=[
            Slider(volume.value, key=f"{key}_slider", min=0, max=100
                   ).on_change(_set_volume),
            ProgressBar(volume.value / 100, key=f"{key}_progress"),
            Text(f"{int(volume.value)}% · a Slider driving a ProgressBar",
                 key=f"{key}_label", size=12, color=Theme.text_secondary),
        ],
    )


def _set_volume(event):
    try:
        volume.value = float(event.get("value", volume.value))
    except (TypeError, ValueError):
        return
    refresh()


def _segments(key: str) -> Widget:
    options = ["Compact", "Comfortable", "Spacious"]
    return Column(
        key=f"{key}_col",
        spacing=Spacing.MD,
        children=[
            SegmentedButton(options, key=f"{key}_seg",
                            selected=segment.value
                            ).on_change(_set_segment),
            Text(f"Selected: {options[segment.value]}",
                 key=f"{key}_label", size=13, weight=600,
                 color=Theme.primary),
        ],
    )


def _set_segment(event):
    try:
        segment.value = int(event.get("value", segment.value))
    except (TypeError, ValueError):
        return
    refresh()


def _submit_form(values: dict) -> None:
    form_note.value = "Welcome aboard, {}!".format(
        str(values.get("name", "")).strip() or "developer")
    refresh()


def _form(key: str) -> Widget:
    form = Form(
        FormField("name",
                  TextField("", key=f"{key}_name", hint="Ada Lovelace",
                            label="Full name"),
                  label="Full name", validators=[required()],
                  helper="Shown on your developer profile"),
        FormField("email",
                  EmailField("", key=f"{key}_email", label="Email"),
                  label="Email",
                  validators=[required(), email_validator()]),
        FormField("site",
                  UrlField("", key=f"{key}_site", label="Website"),
                  label="Website (optional)", validators=[url_validator()]),
        FormField("experience",
                  NumberField("1", key=f"{key}_years", label="Years of Python"),
                  label="Years of Python",
                  validators=[required(), between(0, 60)]),
        FormField("password",
                  PasswordField("", key=f"{key}_pass", label="Password"),
                  label="Password",
                  validators=[required(), min_length(8)]),
        on_submit=_submit_form,
        key=f"{key}_form",
    )
    note = (Text(form_note.value, key=f"{key}_note", size=14, weight=600,
                 color=Theme.primary) if form_note.value
            else Text("Validation runs on submit, then live per field as "
                      "you fix it.", key=f"{key}_hint", size=12,
                      color=Theme.text_secondary))
    return Column(
        key=f"{key}_col",
        spacing=Spacing.MD,
        children=[
            form,
            Button("Create account", key=f"{key}_submit", full_width=True
                   ).on_click(lambda _e: form.submit()),
            note,
        ],
    )


from app.data.catalog import Category, Demo  # noqa: E402

CATEGORY = Category(
    id="inputs",
    name="Inputs & forms",
    icon="edit_note",
    blurb="Text fields, selections, sliders, ratings and live validation.",
    demos=(
        Demo(id="fields", title="Text fields",
             description="Filled, outlined, multiline and every keyboard "
                         "preset.",
             build=_field_kinds, tags=("textfield", "search", "keyboard")),
        Demo(id="selection", title="Selection controls",
             description="Dropdown, radios, checkbox, switch and rating, "
                         "bound to shared state.",
             build=_selections, tags=("dropdown", "radio", "checkbox",
                                      "switch", "rating")),
        Demo(id="slider", title="Sliders & progress",
             description="A Slider driving a ProgressBar in real time.",
             build=_slider_progress, tags=("slider", "progress")),
        Demo(id="segment", title="Segmented buttons",
             description="Connected choices behaving like a radio group.",
             build=_segments, tags=("segment", "choice")),
        Demo(id="form", title="Form & validation",
             description="Required, email, URL, range and length validators "
                         "with live error messages.",
             build=_form, tags=("form", "validate", "submit")),
    ),
)
