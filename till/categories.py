"""Persistent category storage for the till UI."""

from __future__ import annotations

from pathlib import Path

from .config_store import load_json_file, name_key, normalize_name, save_json_file


CONFIG_FILE = Path(__file__).with_name("categories.json")

DEFAULT_CATEGORIES = [
    "beer",
    "spirits",
    "hot drinks",
    "cocktails",
    "wines",
    "snacks",
]

DEFAULT_SUBCATEGORY_MAP = {
    "beer": ["Draught", "Bottled"],
}
def names_match(left: str | None, right: str | None) -> bool:
    return name_key(left) == name_key(right)


def format_display_name(value: str | None) -> str:
    candidate = normalize_name(value)
    if not candidate:
        return ""
    if candidate == candidate.lower():
        return candidate.title()
    return candidate


def resolve_category_name(categories: list[str], category: str | None) -> str:
    candidate = normalize_name(category)
    if not candidate:
        return ""
    for existing in categories:
        if names_match(existing, candidate):
            return existing
    return candidate


def get_subcategories_for_category(
    subcategory_map: dict[str, list[str]],
    category: str | None,
) -> list[str]:
    if not category:
        return []
    resolved_category = resolve_category_name(list(subcategory_map.keys()), category)
    return list(subcategory_map.get(resolved_category, []))


def resolve_subcategory_name(
    subcategory_map: dict[str, list[str]],
    category: str | None,
    subcategory: str | None,
) -> str:
    candidate = normalize_name(subcategory)
    if not candidate:
        return ""
    for existing in get_subcategories_for_category(subcategory_map, category):
        if names_match(existing, candidate):
            return existing
    return candidate


def category_requires_subcategory(
    subcategory_map: dict[str, list[str]],
    category: str | None,
) -> bool:
    return bool(get_subcategories_for_category(subcategory_map, category))


def _normalize_categories(categories: list[str]) -> list[str]:
    unique_categories: list[str] = []
    seen: set[str] = set()
    for category in categories:
        value = str(category).strip()
        if not value:
            continue
        lowered = value.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        unique_categories.append(value)
    return unique_categories


def _normalize_subcategory_map(subcategory_map: dict[str, list[str]]) -> dict[str, list[str]]:
    normalized: dict[str, list[str]] = {}
    for category, subcategories in subcategory_map.items():
        category_name = str(category).strip()
        if not category_name:
            continue
        normalized[category_name] = _normalize_categories(list(subcategories))
    return normalized


def load_category_config(config_path: Path | None = None) -> tuple[list[str], dict[str, list[str]]]:
    path = config_path or CONFIG_FILE
    if not path.exists():
        return list(DEFAULT_CATEGORIES), dict(DEFAULT_SUBCATEGORY_MAP)

    data = load_json_file(path, {})
    if not isinstance(data, dict):
        return list(DEFAULT_CATEGORIES), dict(DEFAULT_SUBCATEGORY_MAP)

    raw_categories = data.get("categories", [])
    if not isinstance(raw_categories, list):
        raw_categories = []
    categories = _normalize_categories(raw_categories)
    if not categories:
        categories = list(DEFAULT_CATEGORIES)

    raw_subcategory_map = dict(DEFAULT_SUBCATEGORY_MAP)
    stored_subcategories = data.get("subcategories", {})
    if isinstance(stored_subcategories, dict):
        raw_subcategory_map.update(_normalize_subcategory_map(stored_subcategories))

    # Match subcategory presets to saved category names case-insensitively so
    # categories such as "Beer" still inherit the default beer subcategories.
    normalized_subcategory_map: dict[str, list[str]] = {}
    lower_key_map = {key.lower(): value for key, value in raw_subcategory_map.items()}
    for category in categories:
        if category in raw_subcategory_map:
            normalized_subcategory_map[category] = raw_subcategory_map[category]
            continue
        matched = lower_key_map.get(category.lower())
        if matched:
            normalized_subcategory_map[category] = matched

    return categories, normalized_subcategory_map


def load_categories(config_path: Path | None = None) -> list[str]:
    categories, _subcategory_map = load_category_config(config_path)
    return categories


def save_categories(categories: list[str], config_path: Path | None = None) -> None:
    _categories, subcategory_map = load_category_config(config_path)
    save_category_config(categories, subcategory_map, config_path)


def save_category_config(
    categories: list[str],
    subcategory_map: dict[str, list[str]],
    config_path: Path | None = None,
) -> None:
    path = config_path or CONFIG_FILE
    unique_categories = _normalize_categories(categories)
    normalized_subcategories = _normalize_subcategory_map(subcategory_map)

    # only keep subcategory entries for categories that still exist
    filtered_subcategories = {
        category: normalized_subcategories.get(category, [])
        for category in unique_categories
        if normalized_subcategories.get(category)
    }

    save_json_file(
        path,
        {
            "categories": unique_categories,
            "subcategories": filtered_subcategories,
        },
    )