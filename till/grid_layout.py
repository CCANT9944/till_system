"""Persistent product grid layout settings for the till UI."""

from __future__ import annotations

from pathlib import Path

from .config_store import load_json_file, save_json_file


CONFIG_FILE = Path(__file__).with_name("grid_layout.json")

DEFAULT_COLUMNS = 6
DEFAULT_ROWS = 6

GRID_LAYOUT_PRESETS = {
    "6 x 6": (6, 6),
    "5 x 6": (5, 6),
    "4 x 6": (4, 6),
}


def _normalize_layout(columns: int, rows: int) -> tuple[int, int]:
    valid_layouts = set(GRID_LAYOUT_PRESETS.values())
    if (columns, rows) in valid_layouts:
        return columns, rows
    return DEFAULT_COLUMNS, DEFAULT_ROWS


def load_grid_layout(config_path: Path | None = None) -> tuple[int, int]:
    path = config_path or CONFIG_FILE
    if not path.exists():
        return DEFAULT_COLUMNS, DEFAULT_ROWS

    data = load_json_file(path, {})
    if not isinstance(data, dict):
        return DEFAULT_COLUMNS, DEFAULT_ROWS

    try:
        columns = int(data.get("columns", DEFAULT_COLUMNS))
        rows = int(data.get("rows", DEFAULT_ROWS))
    except (TypeError, ValueError):
        return DEFAULT_COLUMNS, DEFAULT_ROWS
    return _normalize_layout(columns, rows)


def save_grid_layout(columns: int, rows: int, config_path: Path | None = None) -> None:
    path = config_path or CONFIG_FILE
    columns, rows = _normalize_layout(columns, rows)
    save_json_file(
        path,
        {
            "columns": columns,
            "rows": rows,
        },
    )