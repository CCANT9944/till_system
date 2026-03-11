from interface.till.grid_layout import load_grid_layout, save_grid_layout


def test_grid_layout_defaults_when_missing(tmp_path):
    config_path = tmp_path / "grid_layout.json"
    assert load_grid_layout(config_path) == (6, 6)


def test_grid_layout_round_trip(tmp_path):
    config_path = tmp_path / "grid_layout.json"
    save_grid_layout(4, 6, config_path)
    assert load_grid_layout(config_path) == (4, 6)


def test_invalid_grid_layout_falls_back_to_default(tmp_path):
    config_path = tmp_path / "grid_layout.json"
    save_grid_layout(9, 9, config_path)
    assert load_grid_layout(config_path) == (6, 6)


def test_broken_grid_layout_file_falls_back_to_default(tmp_path):
    config_path = tmp_path / "grid_layout.json"
    config_path.write_text("{oops", encoding="utf-8")
    assert load_grid_layout(config_path) == (6, 6)