from interface.till.color_presets import (
    DEFAULT_CATEGORY_PRESETS,
    DEFAULT_SUBCATEGORY_PRESETS,
    get_preset_color_value,
    load_color_presets,
    save_color_presets,
)


def test_load_defaults_when_file_missing(tmp_path):
    config_path = tmp_path / "missing.json"
    categories, subcategories = load_color_presets(config_path)
    assert categories == DEFAULT_CATEGORY_PRESETS
    assert subcategories == DEFAULT_SUBCATEGORY_PRESETS


def test_save_and_load_custom_presets(tmp_path):
    config_path = tmp_path / "presets.json"
    categories = dict(DEFAULT_CATEGORY_PRESETS)
    categories["beer"] = "#111111"
    subcategories = dict(DEFAULT_SUBCATEGORY_PRESETS)
    subcategories[("beer", "Draught")] = "#222222"

    save_color_presets(categories, subcategories, config_path)
    loaded_categories, loaded_subcategories = load_color_presets(config_path)

    assert loaded_categories["beer"] == "#111111"
    assert loaded_subcategories[("beer", "Draught")] == "#222222"


def test_invalid_preset_file_falls_back_to_defaults(tmp_path):
    config_path = tmp_path / "broken_presets.json"
    config_path.write_text("not json", encoding="utf-8")

    categories, subcategories = load_color_presets(config_path)

    assert categories == DEFAULT_CATEGORY_PRESETS
    assert subcategories == DEFAULT_SUBCATEGORY_PRESETS


def test_case_insensitive_preset_lookup():
    categories = {"Beer": "#111111", "Hot Drinks": "#222222"}
    subcategories = {("Beer", "Draught"): "#333333"}

    assert get_preset_color_value(categories, subcategories, "beer") == "#111111"
    assert get_preset_color_value(categories, subcategories, "BEER", "draught") == "#333333"