"""Read-only database inspection dialog for manager use."""

from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets

from .bill_audit import build_bill_audit_entries
from .categories import format_display_name

CURRENCY = "£"


def _configure_table(table: QtWidgets.QTableWidget, headers: list[str]) -> None:
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setStretchLastSection(True)


def _set_table_data(table: QtWidgets.QTableWidget, rows: list[list[str]]) -> None:
    table.clearContents()
    table.setRowCount(len(rows))
    for row_index, values in enumerate(rows):
        for column_index, value in enumerate(values):
            item = QtWidgets.QTableWidgetItem(value)
            item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            table.setItem(row_index, column_index, item)


def _set_audit_table_data(table: QtWidgets.QTableWidget, rows: list[list[str]]) -> None:
    _set_table_data(table, rows)
    for row_index in range(table.rowCount()):
        changes_item = table.item(row_index, table.columnCount() - 1)
        if changes_item is None:
            continue
        changes_item.setToolTip(changes_item.text())
        if "Removed:" in changes_item.text():
            changes_item.setBackground(QtGui.QColor("#6a2424"))
            changes_item.setForeground(QtGui.QColor("#ffe3e3"))
    table.resizeRowsToContents()


def _format_timestamp(value) -> str:
    if value is None:
        return ""
    return value.strftime("%d/%m/%Y %H:%M")


def build_database_inspector_dialog(parent: QtWidgets.QWidget, db) -> QtWidgets.QDialog:
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle("Database Inspector")
    dialog.resize(920, 640)
    dialog.setStyleSheet(
        "QLabel#databaseInspectorTitle { font-size: 14pt; font-weight: 600; }"
        "QLabel#databaseInspectorHint { font-size: 10pt; color: #9ca3af; }"
        "QGroupBox { font-size: 10pt; font-weight: 600; }"
        "QTableWidget { font-size: 10pt; }"
        "QLabel[databaseValue='true'] { font-weight: 600; }"
    )

    layout = QtWidgets.QVBoxLayout(dialog)
    layout.setContentsMargins(14, 14, 14, 14)
    layout.setSpacing(10)

    title = QtWidgets.QLabel("Database Inspector")
    title.setObjectName("databaseInspectorTitle")
    layout.addWidget(title)

    hint = QtWidgets.QLabel(
        "Review the live till database contents, counts, and recent records without editing them."
    )
    hint.setObjectName("databaseInspectorHint")
    hint.setWordWrap(True)
    layout.addWidget(hint)

    toolbar_layout = QtWidgets.QHBoxLayout()
    toolbar_layout.setContentsMargins(0, 0, 0, 0)
    toolbar_layout.setSpacing(8)
    layout.addLayout(toolbar_layout)

    refresh_button = QtWidgets.QPushButton("Refresh")
    toolbar_layout.addWidget(refresh_button)
    toolbar_layout.addStretch()

    tabs = QtWidgets.QTabWidget()
    layout.addWidget(tabs, 1)

    overview_tab = QtWidgets.QWidget()
    overview_layout = QtWidgets.QVBoxLayout(overview_tab)
    overview_layout.setContentsMargins(0, 0, 0, 0)
    overview_layout.setSpacing(10)
    tabs.addTab(overview_tab, "Overview")

    summary_group = QtWidgets.QGroupBox("Summary")
    summary_layout = QtWidgets.QFormLayout(summary_group)
    summary_layout.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
    summary_layout.setFormAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
    overview_layout.addWidget(summary_group)

    dialog.database_path_value = QtWidgets.QLabel("")
    dialog.database_path_value.setProperty("databaseValue", True)
    dialog.product_count_value = QtWidgets.QLabel("0")
    dialog.product_count_value.setProperty("databaseValue", True)
    dialog.transaction_count_value = QtWidgets.QLabel("0")
    dialog.transaction_count_value.setProperty("databaseValue", True)
    dialog.shift_count_value = QtWidgets.QLabel("0")
    dialog.shift_count_value.setProperty("databaseValue", True)
    dialog.open_shift_value = QtWidgets.QLabel("-")
    dialog.open_shift_value.setProperty("databaseValue", True)
    dialog.backup_count_value = QtWidgets.QLabel("0")
    dialog.backup_count_value.setProperty("databaseValue", True)
    dialog.audit_count_value = QtWidgets.QLabel("0")
    dialog.audit_count_value.setProperty("databaseValue", True)

    summary_layout.addRow("Database file", dialog.database_path_value)
    summary_layout.addRow("Products", dialog.product_count_value)
    summary_layout.addRow("Transactions", dialog.transaction_count_value)
    summary_layout.addRow("Shifts", dialog.shift_count_value)
    summary_layout.addRow("Current open shift", dialog.open_shift_value)
    summary_layout.addRow("Known backups", dialog.backup_count_value)
    summary_layout.addRow("Saved bill audits", dialog.audit_count_value)

    overview_layout.addStretch()

    products_tab = QtWidgets.QWidget()
    products_layout = QtWidgets.QVBoxLayout(products_tab)
    products_layout.setContentsMargins(0, 0, 0, 0)
    products_layout.setSpacing(8)
    dialog.products_table = QtWidgets.QTableWidget()
    _configure_table(
        dialog.products_table,
        ["ID", "Name", "Price", "Category", "Subcategory", "Row", "Col"],
    )
    products_layout.addWidget(dialog.products_table)
    tabs.addTab(products_tab, "Products")

    transactions_tab = QtWidgets.QWidget()
    transactions_layout = QtWidgets.QVBoxLayout(transactions_tab)
    transactions_layout.setContentsMargins(0, 0, 0, 0)
    transactions_layout.setSpacing(8)
    dialog.transactions_table = QtWidgets.QTableWidget()
    _configure_table(
        dialog.transactions_table,
        ["ID", "Timestamp", "Shift", "Payment", "Total", "Units", "Edited"],
    )
    transactions_layout.addWidget(dialog.transactions_table)
    tabs.addTab(transactions_tab, "Transactions")

    transaction_items_tab = QtWidgets.QWidget()
    transaction_items_layout = QtWidgets.QVBoxLayout(transaction_items_tab)
    transaction_items_layout.setContentsMargins(0, 0, 0, 0)
    transaction_items_layout.setSpacing(8)
    dialog.transaction_items_table = QtWidgets.QTableWidget()
    _configure_table(
        dialog.transaction_items_table,
        [
            "Txn ID",
            "Timestamp",
            "Shift",
            "Product ID",
            "Name",
            "Category",
            "Subcategory",
            "Unit Price",
            "Qty",
            "Line Total",
        ],
    )
    transaction_items_layout.addWidget(dialog.transaction_items_table)
    tabs.addTab(transaction_items_tab, "Transaction Items")

    shifts_tab = QtWidgets.QWidget()
    shifts_layout = QtWidgets.QVBoxLayout(shifts_tab)
    shifts_layout.setContentsMargins(0, 0, 0, 0)
    shifts_layout.setSpacing(8)
    dialog.shifts_table = QtWidgets.QTableWidget()
    _configure_table(
        dialog.shifts_table,
        ["ID", "Status", "Opened", "Closed", "Bills", "Total", "Cash", "Card"],
    )
    shifts_layout.addWidget(dialog.shifts_table)
    tabs.addTab(shifts_tab, "Shifts")

    audit_tab = QtWidgets.QWidget()
    audit_layout = QtWidgets.QVBoxLayout(audit_tab)
    audit_layout.setContentsMargins(0, 0, 0, 0)
    audit_layout.setSpacing(8)
    dialog.audit_table = QtWidgets.QTableWidget()
    dialog.audit_table.setWordWrap(True)
    _configure_table(
        dialog.audit_table,
        ["Txn ID", "Shift", "Saved At", "Edit #", "From", "To", "Changes"],
    )
    audit_layout.addWidget(dialog.audit_table)
    tabs.addTab(audit_tab, "Audit")

    close_button = QtWidgets.QPushButton("Close")
    close_button.clicked.connect(dialog.accept)
    layout.addWidget(close_button)

    def refresh_contents() -> None:
        products = sorted(db.list_products(), key=lambda value: (value.id or 0, value.name.lower()))
        transactions = db.list_transactions(limit=100)
        shifts = db.list_shifts(limit=100)
        backup_count = len(db.backups.list_backups())
        transaction_item_rows: list[list[str]] = []
        audit_rows: list[list[str]] = []
        connection = db.conn
        product_count = len(products)
        transaction_count = len(transactions)
        shift_count = len(shifts)
        audit_count = 0
        if connection is not None:
            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM transactions")
            transaction_count = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT COUNT(*) FROM shifts")
            shift_count = int(cursor.fetchone()[0] or 0)
            cursor.execute(
                """
                SELECT
                    transaction_items.transaction_id,
                    transactions.timestamp,
                    transactions.shift_id,
                    transaction_items.product_id,
                    COALESCE(transaction_items.product_name, ''),
                    COALESCE(transaction_items.category, ''),
                    COALESCE(transaction_items.sub_category, ''),
                    COALESCE(transaction_items.unit_price, 0),
                    COALESCE(transaction_items.quantity, 0)
                FROM transaction_items
                INNER JOIN transactions
                    ON transactions.id = transaction_items.transaction_id
                ORDER BY transactions.timestamp DESC, transaction_items.transaction_id DESC, transaction_items.rowid DESC
                LIMIT 200
                """
            )
            transaction_item_rows = [
                [
                    str(row[0] or ""),
                    _format_timestamp(QtCore.QDateTime.fromString(row[1], QtCore.Qt.DateFormat.ISODate).toPyDateTime())
                    if row[1]
                    else "",
                    "" if row[2] is None else str(row[2]),
                    "" if row[3] is None else str(row[3]),
                    row[4],
                    format_display_name(row[5]),
                    format_display_name(row[6]),
                    f"{CURRENCY}{float(row[7] or 0.0):.2f}",
                    str(int(row[8] or 0)),
                    f"{CURRENCY}{float((row[7] or 0.0) * (row[8] or 0)):.2f}",
                ]
                for row in cursor.fetchall()
            ]

        audit_entries: list[tuple[object, list[str]]] = []
        for transaction in db.list_transactions(limit=200):
            revisions = db.list_transaction_revisions(transaction.id)
            audit_count += len(revisions)
            for entry in build_bill_audit_entries(transaction, revisions, currency_symbol=CURRENCY):
                audit_entries.append(
                    (
                        entry.saved_at or QtCore.QDateTime.fromSecsSinceEpoch(0).toPyDateTime(),
                        [
                            str(transaction.id or ""),
                            "" if transaction.shift_id is None else str(transaction.shift_id),
                            _format_timestamp(entry.saved_at),
                            f"#{entry.edit_number}",
                            (
                                f"{_format_timestamp(entry.before_state.timestamp)} | "
                                f"{entry.before_state.payment_method} | {CURRENCY}{entry.before_state.total:.2f}"
                            ),
                            (
                                f"{_format_timestamp(entry.after_state.timestamp)} | "
                                f"{entry.after_state.payment_method} | {CURRENCY}{entry.after_state.total:.2f}"
                            ),
                            "\n".join(entry.lines),
                        ],
                    )
                )
        audit_entries.sort(key=lambda value: value[0], reverse=True)
        audit_rows = [row for _saved_at, row in audit_entries[:200]]

        open_shift = db.get_or_create_open_shift()
        dialog.database_path_value.setText(str(db.path))
        dialog.product_count_value.setText(str(product_count))
        dialog.transaction_count_value.setText(str(transaction_count))
        dialog.shift_count_value.setText(str(shift_count))
        dialog.open_shift_value.setText(f"#{open_shift.id}")
        dialog.backup_count_value.setText(str(backup_count))
        dialog.audit_count_value.setText(str(audit_count))

        _set_table_data(
            dialog.products_table,
            [
                [
                    str(product.id or ""),
                    product.name,
                    f"{CURRENCY}{product.price:.2f}",
                    format_display_name(product.category),
                    format_display_name(product.sub_category),
                    "" if product.tile_row is None else str(product.tile_row),
                    "" if product.tile_column is None else str(product.tile_column),
                ]
                for product in products
            ],
        )
        _set_table_data(
            dialog.transactions_table,
            [
                [
                    str(transaction.id or ""),
                    _format_timestamp(transaction.timestamp),
                    "" if transaction.shift_id is None else str(transaction.shift_id),
                    transaction.payment_method,
                    f"{CURRENCY}{transaction.total:.2f}",
                    str(sum(item.quantity for item in transaction.items)),
                    "Yes" if transaction.edited_at is not None else "No",
                ]
                for transaction in transactions
            ],
        )
        _set_table_data(dialog.transaction_items_table, transaction_item_rows)
        _set_table_data(
            dialog.shifts_table,
            [
                [
                    str(shift.id or ""),
                    "Open" if shift.is_open else "Closed",
                    _format_timestamp(shift.opened_at),
                    _format_timestamp(shift.closed_at),
                    str(shift.transaction_count),
                    f"{CURRENCY}{shift.total:.2f}",
                    f"{CURRENCY}{shift.cash_total:.2f}",
                    f"{CURRENCY}{shift.card_total:.2f}",
                ]
                for shift in shifts
            ],
        )
        _set_audit_table_data(dialog.audit_table, audit_rows)

    dialog.refresh_database_inspector = refresh_contents
    refresh_button.clicked.connect(refresh_contents)
    refresh_contents()
    return dialog


def show_database_inspector_dialog(parent: QtWidgets.QWidget, db) -> None:
    build_database_inspector_dialog(parent, db).exec()