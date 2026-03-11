"""Local application settings helpers for the till UI."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from .config_store import load_json_file, normalize_name


SETTINGS_FILE = Path(__file__).with_name("local_settings.json")
EXAMPLE_SETTINGS_FILE = Path(__file__).with_name("local_settings.example.json")
MANAGER_PIN_ENV = "TILL_MANAGER_PIN"


def _load_settings_dict(path: Path) -> dict[str, object]:
    data = load_json_file(path, {})
    if isinstance(data, dict):
        return data
    return {}


def load_local_settings(
    settings_path: Path | None = None,
    example_path: Path | None = None,
) -> dict[str, object]:
    path = settings_path or SETTINGS_FILE
    if path.exists():
        return _load_settings_dict(path)

    fallback_path = example_path or EXAMPLE_SETTINGS_FILE
    if fallback_path.exists():
        return _load_settings_dict(fallback_path)
    return {}


def load_manager_pin(
    settings_path: Path | None = None,
    example_path: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> str:
    environment = environ or os.environ
    env_pin = normalize_name(environment.get(MANAGER_PIN_ENV))
    if env_pin:
        return env_pin

    settings = load_local_settings(settings_path=settings_path, example_path=example_path)
    return normalize_name(settings.get("manager_pin"))