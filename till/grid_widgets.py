"""Reusable product grid widgets for the till UI."""

from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets

from .models import Product


PRODUCT_TILE_SIZE = 84


def resolve_product_grid_positions(
    products: list[Product], columns: int
) -> list[tuple[Product, int, int]]:
    def is_valid_position(product: Product) -> bool:
        return (
            product.tile_row is not None
            and product.tile_column is not None
            and product.tile_row >= 0
            and 0 <= product.tile_column < columns
        )

    def next_free_cell(occupied: set[tuple[int, int]]) -> tuple[int, int]:
        index = 0
        while True:
            row = index // columns
            col = index % columns
            if (row, col) not in occupied:
                return row, col
            index += 1

    ordered_products = sorted(
        products,
        key=lambda product: (
            0 if is_valid_position(product) else 1,
            product.tile_row if is_valid_position(product) else 10**9,
            product.tile_column if is_valid_position(product) else 10**9,
            product.tile_order or 0,
            product.id or 0,
        ),
    )

    occupied: set[tuple[int, int]] = set()
    positions: list[tuple[Product, int, int]] = []
    for product in ordered_products:
        if is_valid_position(product) and (product.tile_row, product.tile_column) not in occupied:
            row = product.tile_row
            col = product.tile_column
        else:
            row, col = next_free_cell(occupied)
        occupied.add((row, col))
        positions.append((product, row, col))
    return positions


class GridReorderCell(QtWidgets.QFrame):
    def __init__(self, board: "GridReorderBoard", row: int, column: int):
        super().__init__()
        self.board = board
        self.row = row
        self.column = column
        self.product: Product | None = None
        self.drag_start_position: QtCore.QPoint | None = None
        self.setAcceptDrops(True)
        self.setFixedSize(PRODUCT_TILE_SIZE, PRODUCT_TILE_SIZE)
        self.setStyleSheet(
            "QFrame { border: 1px dashed #8b8b8b; border-radius: 6px; background: #f5f5f5; }"
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        self.label = QtWidgets.QLabel("")
        self.label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self.label.setWordWrap(True)
        self.label.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.label)

    def set_product(self, product: Product | None):
        self.product = product
        if product is None:
            self.label.setText("")
            self.setStyleSheet(
                "QFrame { border: 1px dashed #8b8b8b; border-radius: 6px; background: #f5f5f5; }"
            )
            return

        self.label.setText(f"{product.name}\n£{product.price:.2f}")
        font = self.label.font()
        font.setPointSize(product.font_size or 10)
        self.label.setFont(font)
        style = "QFrame { border: 1px solid #3a3a3a; border-radius: 6px;"
        if product.color:
            style += f" background: {product.color};"
            self.label.setStyleSheet("color: white;")
        else:
            style += " background: white;"
            self.label.setStyleSheet("color: black;")
        style += " }"
        self.setStyleSheet(style)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton and self.product is not None:
            self.drag_start_position = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if (
            self.product is None
            or self.drag_start_position is None
            or not (event.buttons() & QtCore.Qt.MouseButton.LeftButton)
        ):
            super().mouseMoveEvent(event)
            return

        if (
            event.position().toPoint() - self.drag_start_position
        ).manhattanLength() < QtWidgets.QApplication.startDragDistance():
            super().mouseMoveEvent(event)
            return

        self.board.start_drag(self)
        self.drag_start_position = None
        super().mouseMoveEvent(event)

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QtGui.QDropEvent):
        if not event.mimeData().hasText():
            event.ignore()
            return
        try:
            product_id = int(event.mimeData().text())
        except ValueError:
            event.ignore()
            return
        self.board.move_product(product_id, self.row, self.column)
        event.acceptProposedAction()


class GridReorderBoard(QtWidgets.QWidget):
    def __init__(self, products: list[Product], columns: int, rows: int, parent=None):
        super().__init__(parent)
        self.columns = columns
        self.rows = rows
        self.products_by_id = {product.id: product for product in products}
        self.product_cells: dict[int, GridReorderCell] = {}
        self.cells: dict[tuple[int, int], GridReorderCell] = {}
        self.layout = QtWidgets.QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(10)

        positions = resolve_product_grid_positions(products, columns)
        max_row = max((row for _, row, _ in positions), default=0)
        self.row_count = max(max_row + 1, ((len(products) + columns - 1) // columns), rows)
        self._ensure_rows(self.row_count)

        for product, row, column in positions:
            self.cells[(row, column)].set_product(product)
            self.product_cells[product.id] = self.cells[(row, column)]

    def _ensure_rows(self, total_rows: int):
        while self.row_count < total_rows:
            self.row_count += 1
        current_rows = len({row for row, _ in self.cells})
        for row in range(current_rows, total_rows):
            for column in range(self.columns):
                cell = GridReorderCell(self, row, column)
                self.layout.addWidget(cell, row, column)
                self.cells[(row, column)] = cell

    def start_drag(self, cell: GridReorderCell):
        if cell.product is None:
            return
        drag = QtGui.QDrag(cell)
        mime = QtCore.QMimeData()
        mime.setText(str(cell.product.id))
        drag.setMimeData(mime)
        drag.setPixmap(cell.grab())
        drag.exec(QtCore.Qt.DropAction.MoveAction)

    def move_product(self, product_id: int, target_row: int, target_column: int):
        source_cell = self.product_cells.get(product_id)
        target_cell = self.cells.get((target_row, target_column))
        if source_cell is None or target_cell is None or source_cell is target_cell:
            return

        source_product = source_cell.product
        target_product = target_cell.product
        target_cell.set_product(source_product)
        self.product_cells[product_id] = target_cell

        source_cell.set_product(target_product)
        if target_product is None:
            return
        self.product_cells[target_product.id] = source_cell

    def get_positions(self) -> list[tuple[Product, int, int]]:
        positions: list[tuple[Product, int, int]] = []
        for (row, column), cell in sorted(self.cells.items()):
            if cell.product is not None:
                positions.append((cell.product, row, column))
        return positions