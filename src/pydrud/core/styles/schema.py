"""
Cross-platform neutral style vocabulary for Pydrud.

This module owns every known style key and its value kind so that both the
static analyser and the .pss stylesheet engine share one source of truth —
write a property inline or in a .pss file and it means exactly the same thing.

Value kinds
-----------
* ``number``  — integer or float (may also accept the string ``"match"`` for
                width/height).
* ``color``   — ARGB hex string, e.g. ``"#FF6366F1"``.
* ``keyword`` — one of a finite set of symbolic values (e.g. ``"start"`` /
                ``"end"``).
* ``composite`` — a nested structure such as an edge-inset dict or a font
                  sub-dict; the analyser accepts any mapping when this is set.
* ``any``     — deliberately unconstrained; the resolver folds or decomposes
                the value (``transform``, ``transition``, ``animation``).

Kebab-case aliases
------------------
Every canonical Python key also accepts a kebab-case spelling (e.g.
``text-align`` → ``text_align``) so .pss authors can write CSS-style keys.
Both normalise to the canonical name here; the renderer sees only the
canonical form.

CSS parity
----------
The vocabulary also carries the CSS long-hand and shorthand spellings a
stylesheet copied from the web uses. Some fold into a Pydrud composite
(``font-size`` → ``font.size``, ``padding-top`` → ``padding.top``,
``border-color`` → ``border.color``); the resolver performs that fold, so the
renderer still sees only the canonical composite form. A few declarations are
genuinely web-only — they are listed in :data:`WEB_ONLY_STYLE_KEYS`, recognised
without an "unknown property" error, and dropped with a single warning.
"""

from __future__ import annotations

_StyleEntry = tuple[str, str]

WEB_ONLY_STYLE_KEYS: frozenset[str] = frozenset({
    "display", "boxSizing", "pointerEvents", "touchAction",
    "appearance", "cursor", "userSelect", "visibility", "float", "clear",
    "whiteSpace", "wordBreak", "textDecoration", "textTransform",
    "objectFit", "listStyle", "flex", "flexDirection", "flexWrap",
    "justifyContent", "alignItems", "alignContent", "alignSelf",
    "flexGrow", "flexShrink", "flexBasis", "order", "rowGap",
    "columnGap", "gridTemplateColumns", "gridTemplateRows", "gridArea",
    "webkitTapHighlightColor", "webkitAppearance", "webkitUserSelect",
    "webkitBoxSizing", "boxShadow", "outline", "textOverflow",
    "fontVariantNumeric", "webkitFontSmoothing", "transitionProperty",
    "borderStyle", "borderCollapse", "borderSpacing", "textIndent",
    "placeItems", "placeContent", "justifyItems", "justifySelf", "fill",
    "stroke", "strokeWidth", "fillRule", "clipPath", "maskImage",
})

VALID_STYLE_KEYS: frozenset[str] = frozenset({
    "bg", "opacity", "width", "height", "minWidth", "maxWidth",
    "minHeight", "maxHeight", "padding", "margin", "border", "borderRadius",
    "font", "textAlign", "alignment", "expand", "visible", "tooltip",
    "rotate", "fit", "bgImage", "elevation", "position", "bottom", "right",
    "top", "left", "spacing", "mainAxis", "crossAxisAlignment", "scroll",
    "variant", "icon", "buttonSize", "disabled", "multiline", "password",
    "readOnly", "keyboard", "activeColor", "color", "thickness",
    "textScale", "status_bar_color", "icon_brightness",
    "borderLeft", "borderRight", "borderTop", "borderBottom",
    "columns", "circular", "divisions", "maxLines", "overflow", "selectable",
    "tristate", "crossAxis", "mainAxisAlignment",

    "animation", "scale", "rotation", "drawerSide", "fabPosition",
    "safeArea", "resizeForKeyboard", "shadow", "aspectRatio", "zIndex",

    "safeAreaTop", "safeAreaBottom", "breakpoint",

    "gradient", "feedback", "role", "pill", "accent", "size",
    "minItemWidth", "maxColumns", "tabletColumns",

    "widthFactor", "heightFactor",

    "borderTopLeftRadius", "borderTopRightRadius",
    "borderBottomLeftRadius", "borderBottomRightRadius",
    "ripple",

    "blur",

    "transition", "transform", "filter",

    "press", "hover", "focus",
    "fontSize", "fontWeight", "fontFamily", "letterSpacing", "lineHeight",
    "paddingTop", "paddingRight", "paddingBottom", "paddingLeft",
    "marginTop", "marginRight", "marginBottom", "marginLeft",
    "borderColor", "borderWidth",
    "overflowX", "overflowY", "transformOrigin",
}) | WEB_ONLY_STYLE_KEYS

KEY_KIND: dict[str, str] = {
    "bg": "color",
    "opacity": "number",
    "width": "number",
    "height": "number",
    "minWidth": "number",
    "maxWidth": "number",
    "minHeight": "number",
    "maxHeight": "number",
    "padding": "composite",
    "margin": "composite",
    "border": "composite",
    "borderRadius": "number",
    "font": "composite",
    "textAlign": "keyword",
    "alignment": "keyword",
    "expand": "number",
    "visible": "keyword",
    "tooltip": "keyword",
    "rotate": "number",
    "fit": "keyword",
    "bgImage": "keyword",
    "elevation": "number",
    "position": "keyword",
    "bottom": "number",
    "right": "number",
    "top": "number",
    "left": "number",
    "spacing": "number",
    "mainAxis": "keyword",
    "crossAxisAlignment": "keyword",
    "scroll": "keyword",
    "variant": "keyword",
    "icon": "keyword",
    "buttonSize": "number",
    "disabled": "keyword",
    "multiline": "keyword",
    "password": "keyword",
    "readOnly": "keyword",
    "keyboard": "keyword",
    "activeColor": "color",
    "color": "color",
    "thickness": "number",
    "textScale": "number",
    "status_bar_color": "color",
    "icon_brightness": "keyword",
    "borderLeft": "number",
    "borderRight": "number",
    "borderTop": "number",
    "borderBottom": "number",
    "columns": "number",
    "circular": "keyword",
    "divisions": "number",
    "maxLines": "number",
    "overflow": "keyword",
    "selectable": "keyword",
    "tristate": "keyword",
    "crossAxis": "number",
    "mainAxisAlignment": "keyword",
    "animation": "any",
    "scale": "number",
    "rotation": "number",
    "drawerSide": "keyword",
    "fabPosition": "keyword",
    "safeArea": "keyword",
    "resizeForKeyboard": "keyword",
    "shadow": "composite",
    "aspectRatio": "number",
    "zIndex": "number",
    "safeAreaTop": "number",
    "safeAreaBottom": "number",
    "breakpoint": "number",
    "gradient": "composite",
    "feedback": "number",
    "role": "keyword",
    "pill": "keyword",
    "accent": "color",
    "size": "number",
    "minItemWidth": "number",
    "maxColumns": "number",
    "tabletColumns": "number",
    "widthFactor": "number",
    "heightFactor": "number",
    "borderTopLeftRadius": "number",
    "borderTopRightRadius": "number",
    "borderBottomLeftRadius": "number",
    "borderBottomRightRadius": "number",
    "ripple": "keyword",
    "blur": "number",

    "transition": "any",
    "transform": "any",
    "filter": "any",
    "press": "composite",
    "hover": "composite",
    "focus": "composite",
    "fontSize": "number",
    "fontWeight": "number",
    "fontFamily": "keyword",
    "letterSpacing": "number",
    "lineHeight": "number",
    "paddingTop": "number",
    "paddingRight": "number",
    "paddingBottom": "number",
    "paddingLeft": "number",
    "marginTop": "number",
    "marginRight": "number",
    "marginBottom": "number",
    "marginLeft": "number",
    "borderColor": "color",
    "borderWidth": "number",
    "overflowX": "keyword",
    "overflowY": "keyword",
    "transformOrigin": "keyword",
}

_KEBAB_CANONICAL: dict[str, str] = {
    "text-align": "textAlign",
    "min-width": "minWidth",
    "max-width": "maxWidth",
    "min-height": "minHeight",
    "max-height": "maxHeight",
    "border-radius": "borderRadius",
    "text-scale": "textScale",
    "status-bar-color": "status_bar_color",
    "icon-brightness": "icon_brightness",
    "border-left": "borderLeft",
    "border-right": "borderRight",
    "border-top": "borderTop",
    "border-bottom": "borderBottom",
    "cross-axis": "crossAxis",
    "main-axis": "mainAxis",
    "main-axis-align": "mainAxisAlignment",
    "cross-axis-align": "crossAxisAlignment",
    "safe-area-top": "safeAreaTop",
    "safe-area-bottom": "safeAreaBottom",
    "width-factor": "widthFactor",
    "height-factor": "heightFactor",
    "min-item-width": "minItemWidth",
    "max-columns": "maxColumns",
    "tablet-columns": "tabletColumns",
    "border-top-left-radius": "borderTopLeftRadius",
    "border-top-right-radius": "borderTopRightRadius",
    "border-bottom-left-radius": "borderBottomLeftRadius",
    "border-bottom-right-radius": "borderBottomRightRadius",

    "background": "bg",
    "background-color": "bg",
    "background-image": "bgImage",
    "font-size": "fontSize",
    "font-weight": "fontWeight",
    "font-family": "fontFamily",
    "letter-spacing": "letterSpacing",
    "line-height": "lineHeight",

    "padding-top": "paddingTop",
    "padding-right": "paddingRight",
    "padding-bottom": "paddingBottom",
    "padding-left": "paddingLeft",
    "margin-top": "marginTop",
    "margin-right": "marginRight",
    "margin-bottom": "marginBottom",
    "margin-left": "marginLeft",
    "border-color": "borderColor",
    "border-width": "borderWidth",
    "border-style": "borderStyle",

    "z-index": "zIndex",
    "aspect-ratio": "aspectRatio",
    "transform-origin": "transformOrigin",
    "overflow-x": "overflowX",
    "overflow-y": "overflowY",
    "box-sizing": "boxSizing",
    "box-shadow": "boxShadow",
    "pointer-events": "pointerEvents",
    "touch-action": "touchAction",
    "user-select": "userSelect",
    "text-decoration": "textDecoration",
    "text-transform": "textTransform",
    "text-overflow": "textOverflow",
    "white-space": "whiteSpace",
    "word-break": "wordBreak",
    "object-fit": "objectFit",
    "list-style": "listStyle",
    "font-variant-numeric": "fontVariantNumeric",
    "flex-direction": "flexDirection",
    "flex-wrap": "flexWrap",
    "justify-content": "justifyContent",
    "align-items": "alignItems",
    "align-content": "alignContent",
    "align-self": "alignSelf",
    "flex-grow": "flexGrow",
    "flex-shrink": "flexShrink",
    "flex-basis": "flexBasis",
    "row-gap": "rowGap",
    "column-gap": "columnGap",

    "gap": "spacing",
    "place-items": "placeItems",
    "place-content": "placeContent",
}

_VENDOR_PREFIXES = ("-webkit-", "-moz-", "-ms-", "-o-")

def normalize_key(key: str) -> str | None:
    """Normalise a style key to its canonical Python form, or ``None`` if unknown."""
    if key in VALID_STYLE_KEYS:
        return key
    canonical = _KEBAB_CANONICAL.get(key)
    if canonical is not None:
        return canonical
    for prefix in _VENDOR_PREFIXES:
        if key.startswith(prefix):
            stripped = key[len(prefix):]

            resolved = normalize_key(stripped)
            if resolved is not None:
                return resolved
            return "webkit" + _camel(stripped)
    return None

def _camel(name: str) -> str:
    """``tap-highlight-color`` → ``TapHighlightColor``."""
    return "".join(part[:1].upper() + part[1:] for part in name.split("-"))
