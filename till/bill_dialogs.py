"""Bill editing dialog helpers for the till UI."""

from __future__ import annotations

import datetime

from PyQt6 import QtCore, QtGui, QtWidgets

from .dialog_helpers import choose_product_dialog
from .models import Product
from .models import Transaction, TransactionItem
from .payments import CHECKOUT_PAYMENT_METHODS

CURRENCY = "£"
ADDED_ROW_COLOR = QtGui.QColor("#17351f")
EDITED_ROW_COLOR = QtGui.QColor("#5a4321")
HIGHLIGHT_TEXT_COLOR = QtGui.QColor("#f8fafc")


def prompt_edit_bill(
    parent: QtWidgets.QWidget,
    transaction: Transaction,
) -> Transaction | None:
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle(f"Edit Bill #{transaction.id or '-'}")
    dialog.resize(720, 480)

    layout = QtWidgets.QVBoxLayout(dialog)

    payment_layout = QtWidgets.QFormLayout()
    layout.addLayout(payment_layout)
    payment_combo = QtWidgets.QComboBox()
    payment_options = list(CHECKOUT_PAYMENT_METHODS)
    if transaction.payment_method not in payment_options:
        payment_options.append(transaction.payment_method)
    payment_combo.addItems(payment_options)
    payment_combo.setCurrentText(transaction.payment_method)
    payment_layout.addRow("Payment Method", payment_combo)

    timestamp_edit = QtWidgets.QDateTimeEdit()
    timestamp_edit.setCalendarPopup(True)
    timestamp_edit.setDisplayFormat("dd/MM/yyyy HH:mm")
    timestamp_edit.setDateTime(
        QtCore.QDateTime.fromString(
            transaction.timestamp.isoformat(timespec="seconds"),
            QtCore.Qt.DateFormat.ISODate,
        )
    )
    payment_layout.addRow("Bill Time", timestamp_edit)

    original_items = [
        TransactionItem(
            product_id=item.product_id,
            product_name=item.product_name,
            unit_price=item.unit_price,
            quantity=item.quantity,
            category=item.category,
            sub_category=item.sub_category,
        )
        for item in transaction.items
    ]

    table = QtWidgets.QTableWidget(len(transaction.items), 5)
    table.setHorizontalHeaderLabels(["Item", "Qty", "Unit Price", "Line Total", "Change"])
    table.verticalHeader().setVisible(False)
    table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
    table.horizontalHeader().setStretchLastSection(False)
    table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
    layout.addWidget(table, 1)

    total_label = QtWidgets.QLabel(f"Total: {CURRENCY}0.00")
    layout.addWidget(total_label)

    removed_group = QtWidgets.QGroupBox("Removed Items")
    removed_layout = QtWidgets.QVBoxLayout(removed_group)
    removed_layout.setContentsMargins(8, 8, 8, 8)
    removed_layout.setSpacing(6)
    removed_items_list = QtWidgets.QListWidget()
    removed_items_list.setObjectName("removedItemsList")
    removed_items_list.setStyleSheet("font-size: 10pt; color: #fca5a5;")
    removed_layout.addWidget(removed_items_list)
    removed_group.hide()
    layout.addWidget(removed_group)

    button_row = QtWidgets.QHBoxLayout()
    layout.addLayout(button_row)
    add_item_button = QtWidgets.QPushButton("Add Item")
    remove_item_button = QtWidgets.QPushButton("Remove Selected")
    button_row.addWidget(add_item_button)
    button_row.addWidget(remove_item_button)
    button_row.addStretch()

    button_box = QtWidgets.QDialogButtonBox(
        QtWidgets.QDialogButtonBox.StandardButton.Save
        | QtWidgets.QDialogButtonBox.StandardButton.Cancel
    )
    layout.addWidget(button_box)

    updating = {"active": False}

    def ensure_line_total_item(row: int) -> QtWidgets.QTableWidgetItem:
        item = table.item(row, 3)
        if item is None:
            item = QtWidgets.QTableWidgetItem(f"{CURRENCY}0.00")
            item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 3, item)
        return item

    def ensure_change_item(row: int) -> QtWidgets.QTableWidgetItem:
        item = table.item(row, 4)
        if item is None:
            item = QtWidgets.QTableWidgetItem("")
            item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 4, item)
        return item

    def set_item_style(item: QtWidgets.QTableWidgetItem | None, color: QtGui.QColor | None) -> None:
        if item is None:
            return
        if color is None:
            item.setBackground(QtGui.QBrush())
            item.setForeground(QtGui.QBrush())
            return
        item.setBackground(color)
        item.setForeground(HIGHLIGHT_TEXT_COLOR)

    def format_item_summary(item: TransactionItem) -> str:
        return f"{item.product_name} x{item.quantity} @ {CURRENCY}{item.unit_price:.2f} = {CURRENCY}{item.line_total:.2f}"

    def set_row_values(
        row: int,
        item: TransactionItem | None = None,
        *,
        original_index: int | None = None,
    ) -> None:
        transaction_item = item or TransactionItem()
        name_item = QtWidgets.QTableWidgetItem(transaction_item.product_name)
        name_item.setData(
            QtCore.Qt.ItemDataRole.UserRole,
            {
                "product_id": transaction_item.product_id,
                "category": transaction_item.category,
                "sub_category": transaction_item.sub_category,
                "original_index": original_index,
            },
        )
        qty_item = QtWidgets.QTableWidgetItem(str(transaction_item.quantity or 1))
        price_item = QtWidgets.QTableWidgetItem(f"{transaction_item.unit_price:.2f}")
        table.setItem(row, 0, name_item)
        table.setItem(row, 1, qty_item)
        table.setItem(row, 2, price_item)
        ensure_line_total_item(row)
        ensure_change_item(row)

    def parse_int(value: str) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def parse_float(value: str) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def recalculate_totals() -> None:
        if updating["active"]:
            return
        updating["active"] = True
        total = 0.0
        for row in range(table.rowCount()):
            qty_item = table.item(row, 1)
            price_item = table.item(row, 2)
            quantity = parse_int(qty_item.text().strip()) if qty_item is not None else None
            unit_price = parse_float(price_item.text().strip()) if price_item is not None else None
            line_total = 0.0
            if quantity is not None and quantity > 0 and unit_price is not None and unit_price >= 0:
                line_total = quantity * unit_price
            ensure_line_total_item(row).setText(f"{CURRENCY}{line_total:.2f}")
            total += line_total
        total_label.setText(f"Total: {CURRENCY}{total:.2f}")

        current_original_indices: set[int] = set()
        for row in range(table.rowCount()):
            name_item = table.item(row, 0)
            qty_item = table.item(row, 1)
            price_item = table.item(row, 2)
            line_total_item = ensure_line_total_item(row)
            change_item = ensure_change_item(row)
            metadata = name_item.data(QtCore.Qt.ItemDataRole.UserRole) if name_item is not None else None
            metadata = metadata if isinstance(metadata, dict) else {}
            original_index = metadata.get("original_index")
            quantity = parse_int(qty_item.text().strip()) if qty_item is not None else None
            unit_price = parse_float(price_item.text().strip()) if price_item is not None else None

            if original_index is None:
                change_item.setText("Added")
                for column in range(table.columnCount()):
                    set_item_style(table.item(row, column), ADDED_ROW_COLOR)
                continue

            current_original_indices.add(int(original_index))
            original_item = original_items[int(original_index)]
            changed_columns: set[int] = set()
            changed_fields: list[str] = []

            current_name = name_item.text().strip() if name_item is not None else ""
            if current_name != original_item.product_name:
                changed_columns.add(0)
                changed_fields.append("Name")
            if quantity != original_item.quantity:
                changed_columns.add(1)
                changed_fields.append("Qty")
            if unit_price is None or abs(unit_price - original_item.unit_price) > 0.0001:
                changed_columns.add(2)
                changed_fields.append("Price")
            if changed_columns:
                changed_columns.add(3)
                change_item.setText(", ".join(changed_fields))
                for column in range(table.columnCount()):
                    color = EDITED_ROW_COLOR if column in changed_columns or column == 4 else None
                    set_item_style(table.item(row, column), color)
            else:
                change_item.setText("")
                for column in range(table.columnCount()):
                    set_item_style(table.item(row, column), None)

        removed_items_list.clear()
        removed_indexes = [
            index for index in range(len(original_items)) if index not in current_original_indices
        ]
        for index in removed_indexes:
            removed_items_list.addItem(format_item_summary(original_items[index]))
        removed_group.setVisible(bool(removed_indexes))
        updating["active"] = False

    def highlight_row(row: int) -> None:
        if row < 0 or row >= table.rowCount():
            return
        table.clearSelection()
        table.selectRow(row)
        table.setCurrentCell(row, 0)
        item = table.item(row, 0)
        if item is not None:
            table.scrollToItem(item)
        table.setFocus()

    def add_row_from_product(product: Product) -> None:
        row = table.rowCount()
        table.insertRow(row)
        set_row_values(
            row,
            TransactionItem(
                product_id=product.id,
                product_name=product.name,
                unit_price=product.price,
                quantity=1,
                category=product.category,
                sub_category=product.sub_category,
            ),
        )
        recalculate_totals()
        highlight_row(row)

    def choose_inventory_product() -> Product | None:
        inventory = getattr(parent, "inventory", None)
        if inventory is None or not hasattr(inventory, "list_products"):
            QtWidgets.QMessageBox.information(
                dialog,
                "Edit Bill",
                "Inventory search is not available from this screen.",
            )
            return None
        products = sorted(inventory.list_products(), key=lambda product: product.name.lower())
        return choose_product_dialog(
            dialog,
            products,
            "Add item to bill",
            "Search for a product to add to this bill:",
            currency_symbol=CURRENCY,
        )

    def add_row_by_search() -> None:
        product = choose_inventory_product()
        if product is None:
            return
        add_row_from_product(product)

    def remove_selected_row() -> None:
        row = table.currentRow()
        if row < 0:
            return
        table.removeRow(row)
        recalculate_totals()
        if table.rowCount() > 0:
            highlight_row(min(row, table.rowCount() - 1))

    def collect_items() -> list[TransactionItem] | None:
        collected: list[TransactionItem] = []
        for row in range(table.rowCount()):
            name_item = table.item(row, 0)
            qty_item = table.item(row, 1)
            price_item = table.item(row, 2)
            name = name_item.text().strip() if name_item is not None else ""
            quantity_text = qty_item.text().strip() if qty_item is not None else ""
            price_text = price_item.text().strip() if price_item is not None else ""

            if not name and not quantity_text and not price_text:
                continue
            if not name:
                QtWidgets.QMessageBox.warning(dialog, "Edit Bill", "Each bill item needs a name.")
                return None

            quantity = parse_int(quantity_text)
            if quantity is None or quantity <= 0:
                QtWidgets.QMessageBox.warning(dialog, "Edit Bill", "Each bill item needs a quantity above zero.")
                return None

            unit_price = parse_float(price_text)
            if unit_price is None or unit_price < 0:
                QtWidgets.QMessageBox.warning(dialog, "Edit Bill", "Each bill item needs a valid unit price.")
                return None

            metadata = name_item.data(QtCore.Qt.ItemDataRole.UserRole) if name_item is not None else None
            metadata = metadata if isinstance(metadata, dict) else {}
            collected.append(
                TransactionItem(
                    product_id=metadata.get("product_id"),
                    product_name=name,
                    unit_price=unit_price,
                    quantity=quantity,
                    category=metadata.get("category", ""),
                    sub_category=metadata.get("sub_category", ""),
                )
            )
        if not collected:
            QtWidgets.QMessageBox.warning(dialog, "Edit Bill", "A bill must contain at least one item.")
            return None
        return collected

    def save_bill() -> None:
        items = collect_items()
        if items is None:
            return
        timestamp = timestamp_edit.dateTime().toPyDateTime()
        if isinstance(timestamp, datetime.date) and not isinstance(timestamp, datetime.datetime):
            timestamp = datetime.datetime.combine(timestamp, datetime.time())
        dialog.setProperty(
            "result_transaction",
            Transaction(
                id=transaction.id,
                items=items,
                total=sum(item.line_total for item in items),
                payment_method=payment_combo.currentText(),
                shift_id=transaction.shift_id,
                timestamp=timestamp,
            ),
        )
        dialog.accept()

    for row_index, item in enumerate(transaction.items):
        set_row_values(row_index, item, original_index=row_index)

    table.itemChanged.connect(lambda _item: recalculate_totals())
    add_item_button.clicked.connect(add_row_by_search)
    remove_item_button.clicked.connect(remove_selected_row)
    button_box.accepted.connect(save_bill)
    button_box.rejected.connect(dialog.reject)
    recalculate_totals()

    if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return None
    return dialog.property("result_transaction")