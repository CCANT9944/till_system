"""Shared helpers for resilient JSON-backed configuration files."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any


def normalize_name(value: str | None) -> str:
    return str(value or "").strip()


def name_key(value: str | None) -> str:
    return normalize_name(value).casefold()


def load_json_file(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError, TypeError, ValueError):
        return default


def save_json_file(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        suffix=".tmp",
    ) as handle:
        json.dump(data, handle, indent=2)
        temp_path = Path(handle.name)
    temp_path.replace(path)