"""Theme tokens shared by configuration validation and stylesheet generation."""

import re
from pathlib import Path, PurePosixPath

DEFAULT_TOKENS = {
    "accent_color": "#2459a6",
    "accent_hover": "#173d78",
    "background": "#f5f7fa",
    "surface": "#ffffff",
    "text_color": "#202b3a",
    "muted_color": "#647084",
    "border_color": "#dce2ea",
    "code_background": "#edf1f6",
    "font_family": (
        'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    ),
    "mono_font_family": 'ui-monospace, "Cascadia Code", Consolas, monospace',
    "content_width": "56rem",
}
PRESETS = {
    "default": {},
    "docs": {
        "accent_color": "#087f78",
        "accent_hover": "#065f59",
        "background": "#fafbfc",
        "text_color": "#24292f",
        "muted_color": "#57606a",
        "border_color": "#d0d7de",
        "code_background": "#f0f3f6",
        "content_width": "64rem",
    },
}


def normalize_theme(value: object, site_root: Path) -> dict:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ValueError("theme must be a mapping with string keys")
    unknown = value.keys() - {"preset", "custom_css", *DEFAULT_TOKENS}
    if unknown:
        raise ValueError(f"theme: unknown fields: {', '.join(sorted(unknown))}")
    preset = value.get("preset", "default")
    if not isinstance(preset, str) or preset not in PRESETS:
        raise ValueError("theme.preset must be one of: default, docs")
    tokens = {**DEFAULT_TOKENS, **PRESETS[preset]}
    for name in DEFAULT_TOKENS.keys() & value.keys():
        token = value[name]
        valid = isinstance(token, str)
        if valid and name.endswith("font_family"):
            valid = bool(re.fullmatch(r"[\w ,.'\"-]+", token)) and bool(token.strip())
        elif valid and name == "content_width":
            valid = bool(re.fullmatch(r"[1-9]\d{0,3}(?:\.\d+)?(?:rem|px|ch)", token))
        elif valid:
            valid = bool(re.fullmatch(r"#(?:[\da-fA-F]{3}|[\da-fA-F]{6})", token))
        if not valid:
            raise ValueError(f"theme.{name} has an invalid CSS value")
        tokens[name] = token
    custom_css = value.get("custom_css", [])
    if not isinstance(custom_css, list):
        raise ValueError("theme.custom_css must be a list of paths relative to static/")
    static_root = (site_root / "static").resolve()
    for item in custom_css:
        if not isinstance(item, str) or not item or "\\" in item:
            raise ValueError("theme.custom_css must contain relative CSS paths")
        relative = PurePosixPath(item)
        source = (static_root / item).resolve()
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or ":" in item
            or relative.suffix.lower() != ".css"
            or not source.is_relative_to(static_root)
            or not source.is_file()
        ):
            raise ValueError(f"theme.custom_css: not a CSS file inside static/: {item}")
    return {"preset": preset, **tokens, "custom_css": custom_css}


def theme_css(theme: dict) -> str:
    declarations = "\n".join(
        f"  --naru-{name.replace('_', '-')}: {theme[name]};" for name in DEFAULT_TOKENS
    )
    return f":root {{\n{declarations}\n}}\n"