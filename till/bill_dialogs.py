"""Bill editing dialog helpers for the till UI."""

from __future__ import annotations

import datetime

from PyQt6 import QtCore, QtWidgets

from .models import Transaction, TransactionItem
from .payments import CHECKOUT_PAYMENT_METHODS

CURRENCY = "£"


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

    table = QtWidgets.QTableWidget(len(transaction.items), 4)
    table.setHorizontalHeaderLabels(["Item", "Qty", "Unit Price", "Line Total"])
    table.verticalHeader().setVisible(False)
    table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
    table.horizontalHeader().setStretchLastSection(False)
    table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
    layout.addWidget(table, 1)

    total_label = QtWidgets.QLabel(f"Total: {CURRENCY}0.00")
    layout.addWidget(total_label)

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

    def set_row_values(row: int, item: TransactionItem | None = None) -> None:
        transaction_item = item or TransactionItem()
        name_item = QtWidgets.QTableWidgetItem(transaction_item.product_name)
        name_item.setData(
            QtCore.Qt.ItemDataRole.UserRole,
            {
                "product_id": transaction_item.product_id,
                "category": transaction_item.category,
                "sub_category": transaction_item.sub_category,
            },
        )
        qty_item = QtWidgets.QTableWidgetItem(str(transaction_item.quantity or 1))
        price_item = QtWidgets.QTableWidgetItem(f"{transaction_item.unit_price:.2f}")
        table.setItem(row, 0, name_item)
        table.setItem(row, 1, qty_item)
        table.setItem(row, 2, price_item)
        ensure_line_total_item(row)

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
        updating["active"] = False

    def add_row() -> None:
        row = table.rowCount()
        table.insertRow(row)
        set_row_values(row)
        recalculate_totals()

    def remove_selected_row() -> None:
        row = table.currentRow()
        if row < 0:
            return
        table.removeRow(row)
        if table.rowCount() == 0:
            add_row()
        recalculate_totals()

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
        set_row_values(row_index, item)

    if table.rowCount() == 0:
        add_row()

    table.itemChanged.connect(lambda _item: recalculate_totals())
    add_item_button.clicked.connect(add_row)
    remove_item_button.clicked.connect(remove_selected_row)
    button_box.accepted.connect(save_bill)
    button_box.rejected.connect(dialog.reject)
    recalculate_totals()

    if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return None
    return dialog.property("result_transaction")