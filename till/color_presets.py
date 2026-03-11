"""Persistent color preset storage for the till UI."""

from __future__ import annotations

from pathlib import Path

from .config_store import load_json_file, name_key, save_json_file


CONFIG_FILE = Path(__file__).with_name("color_presets.json")

DEFAULT_CATEGORY_PRESETS = {
    "beer": "#D4A017",
    "spirits": "#8B5CF6",
    "hot drinks": "#B45309",
    "cocktails": "#DB2777",
    "wines": "#7F1D1D",
    "snacks": "#F97316",
}

DEFAULT_SUBCATEGORY_PRESETS = {
    ("beer", "Draught"): "#C69214",
    ("beer", "Bottled"): "#9A6B16",
}
def get_preset_color_value(
    category_presets: dict[str, str],
    subcategory_presets: dict[tuple[str, str], str],
    category: str,
    subcategory: str = "",
) -> str:
    category_key = name_key(category)
    subcategory_key = name_key(subcategory)

    if subcategory_key:
        for (existing_category, existing_subcategory), color in subcategory_presets.items():
            if name_key(existing_category) == category_key and name_key(existing_subcategory) == subcategory_key:
                return color

    for existing_category, color in category_presets.items():
        if name_key(existing_category) == category_key:
            return color
    return ""


def _encode_subcategory_key(category: str, subcategory: str) -> str:
    return f"{category}::{subcategory}"


def _decode_subcategory_key(key: str) -> tuple[str, str]:
    category, subcategory = key.split("::", 1)
    return category, subcategory


def load_color_presets(config_path: Path | None = None) -> tuple[dict[str, str], dict[tuple[str, str], str]]:
    """Load presets from disk, falling back to defaults when not configured."""
    path = config_path or CONFIG_FILE
    category_presets = dict(DEFAULT_CATEGORY_PRESETS)
    subcategory_presets = dict(DEFAULT_SUBCATEGORY_PRESETS)

    if not path.exists():
        return category_presets, subcategory_presets

    data = load_json_file(path, {})
    if not isinstance(data, dict):
        return category_presets, subcategory_presets

    stored_categories = data.get("categories", {})
    if isinstance(stored_categories, dict):
        category_presets.update({str(key): str(value) for key, value in stored_categories.items()})

    encoded_subcategories = data.get("subcategories", {})
    if isinstance(encoded_subcategories, dict):
        for key, value in encoded_subcategories.items():
            try:
                subcategory_presets[_decode_subcategory_key(str(key))] = str(value)
            except ValueError:
                continue
    return category_presets, subcategory_presets


def save_color_presets(
    category_presets: dict[str, str],
    subcategory_presets: dict[tuple[str, str], str],
    config_path: Path | None = None,
) -> None:
    """Save presets to disk as JSON."""
    path = config_path or CONFIG_FILE
    data = {
        "categories": dict(sorted(category_presets.items())),
        "subcategories": {
            _encode_subcategory_key(category, subcategory): color
            for (category, subcategory), color in sorted(subcategory_presets.items())
        },
    }
    save_json_file(path, data)