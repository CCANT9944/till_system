"""Compatibility wrapper that exposes the top-level till package as interface.till."""

from __future__ import annotations

from pathlib import Path

from till import run


__path__ = [str(Path(__file__).resolve().parents[2] / "till")]

__all__ = ["run"]