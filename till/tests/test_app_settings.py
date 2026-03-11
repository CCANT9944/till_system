from interface.till.app_settings import load_local_settings, load_manager_pin


def test_load_manager_pin_prefers_environment_over_files(tmp_path):
    settings_path = tmp_path / "local_settings.json"
    settings_path.write_text('{"manager_pin": "1111"}', encoding="utf-8")

    manager_pin = load_manager_pin(
        settings_path=settings_path,
        environ={"TILL_MANAGER_PIN": "2468"},
    )

    assert manager_pin == "2468"


def test_load_manager_pin_uses_ignored_local_settings_file(tmp_path):
    settings_path = tmp_path / "local_settings.json"
    settings_path.write_text('{"manager_pin": "1357"}', encoding="utf-8")

    manager_pin = load_manager_pin(settings_path=settings_path, environ={})

    assert manager_pin == "1357"


def test_load_local_settings_falls_back_to_example_template(tmp_path):
    example_path = tmp_path / "local_settings.example.json"
    example_path.write_text('{"manager_pin": "0000"}', encoding="utf-8")

    settings = load_local_settings(
        settings_path=tmp_path / "missing_local_settings.json",
        example_path=example_path,
    )

    assert settings == {"manager_pin": "0000"}