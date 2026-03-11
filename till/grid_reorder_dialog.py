"""Grid reorder dialog shell for the till UI."""

from __future__ import annotations

from PyQt6 import QtWidgets

from .grid_widgets import GridReorderBoard
from .models import Product


def show_grid_reorder_dialog(
    parent: QtWidgets.QWidget,
    products: list[Product],
    category: str,
    subcategory: str | None,
    grid_columns: int,
    grid_rows: int,
) -> list[tuple[Product, int, int]] | None:
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle("Rearrange Grid Items")
    dialog.resize(900, 760)

    layout = QtWidgets.QVBoxLayout(dialog)
    title = category.capitalize()
    if subcategory:
        title = f"{title} / {subcategory}"
    layout.addWidget(
        QtWidgets.QLabel(
            f"Drag and drop each tile into the exact grid cell you want for {title}."
        )
    )

    scroll = QtWidgets.QScrollArea()
    scroll.setWidgetResizable(True)
    board = GridReorderBoard(products, grid_columns, grid_rows, dialog)
    scroll.setWidget(board)
    layout.addWidget(scroll)

    close_row = QtWidgets.QHBoxLayout()
    layout.addLayout(close_row)
    save_button = QtWidgets.QPushButton("Save")
    cancel_button = QtWidgets.QPushButton("Cancel")
    close_row.addWidget(save_button)
    close_row.addWidget(cancel_button)

    save_button.clicked.connect(dialog.accept)
    cancel_button.clicked.connect(dialog.reject)

    if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return None

    return board.get_positions()