from interface.till.categories import (
    DEFAULT_CATEGORIES,
    DEFAULT_SUBCATEGORY_MAP,
    get_subcategories_for_category,
    load_categories,
    load_category_config,
    resolve_category_name,
    resolve_subcategory_name,
    save_categories,
    save_category_config,
)


def test_load_default_categories_when_missing(tmp_path):
    path = tmp_path / "missing_categories.json"
    categories = load_categories(path)
    assert categories == DEFAULT_CATEGORIES

    loaded_categories, loaded_subcategories = load_category_config(path)
    assert loaded_categories == DEFAULT_CATEGORIES
    assert loaded_subcategories == DEFAULT_SUBCATEGORY_MAP


def test_save_and_load_custom_categories(tmp_path):
    path = tmp_path / "categories.json"
    save_categories(["beer", "snacks", "snacks", "coffee"], path)
    categories = load_categories(path)
    assert categories == ["beer", "snacks", "coffee"]


def test_save_and_load_subcategory_map(tmp_path):
    path = tmp_path / "categories_with_subcategories.json"
    save_category_config(
        ["coffee", "beer", "snacks"],
        {
            "beer": ["Cans", "Draught", "Cans"],
            "coffee": ["Small", "Large"],
            "unused": ["x"],
        },
        path,
    )

    categories, subcategory_map = load_category_config(path)
    assert categories == ["coffee", "beer", "snacks"]
    assert subcategory_map["beer"] == ["Cans", "Draught"]
    assert subcategory_map["coffee"] == ["Small", "Large"]
    assert "unused" not in subcategory_map


def test_capitalized_category_keeps_default_subcategories(tmp_path):
    path = tmp_path / "capitalized_categories.json"
    save_category_config(["Beer", "Spirits"], {}, path)

    categories, subcategory_map = load_category_config(path)

    assert categories == ["Beer", "Spirits"]
    assert subcategory_map["Beer"] == ["Draught", "Bottled"]


def test_category_resolution_helpers_are_case_insensitive(tmp_path):
    path = tmp_path / "capitalized_categories.json"
    save_category_config(["Beer", "Hot Drinks"], {"Beer": ["Draught", "Bottled"]}, path)

    categories, subcategory_map = load_category_config(path)

    assert resolve_category_name(categories, "beer") == "Beer"
    assert resolve_category_name(categories, "HOT DRINKS") == "Hot Drinks"
    assert get_subcategories_for_category(subcategory_map, "beer") == ["Draught", "Bottled"]
    assert resolve_subcategory_name(subcategory_map, "BEER", "draught") == "Draught"


def test_invalid_category_file_falls_back_to_defaults(tmp_path):
    path = tmp_path / "broken_categories.json"
    path.write_text("{not valid json", encoding="utf-8")

    categories, subcategory_map = load_category_config(path)

    assert categories == DEFAULT_CATEGORIES
    assert subcategory_map == DEFAULT_SUBCATEGORY_MAP