"""Helpers for rebuilding simple exclusive button rows in the till UI."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6 import QtWidgets


def clear_layout_widgets(layout: QtWidgets.QLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget:
            widget.deleteLater()


def rebuild_toggle_button_row(
    layout: QtWidgets.QLayout,
    labels: list[str],
    on_click: Callable[[str, bool], None],
) -> dict[str, QtWidgets.QPushButton]:
    clear_layout_widgets(layout)
    buttons: dict[str, QtWidgets.QPushButton] = {}
    for label in labels:
        button = QtWidgets.QPushButton(label)
        button.setCheckable(True)
        button.clicked.connect(lambda checked, value=label: on_click(value, checked))
        layout.addWidget(button)
        buttons[label] = button
    return buttons


def sync_exclusive_button_row(
    buttons: dict[str, QtWidgets.QPushButton],
    selected_value: str | None,
) -> None:
    for value, button in buttons.items():
        button.setChecked(value == selected_value)