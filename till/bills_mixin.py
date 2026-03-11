"""Bills tab UI and report helpers for the till."""

from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets

from .bill_dialogs import prompt_edit_bill
from .models import Transaction

CURRENCY = "£"


class BillsMixin:
    def build_bills_tab(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        self.bills_tab.setLayout(layout)

        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.setSpacing(8)
        layout.addLayout(filter_layout)
        filter_label = QtWidgets.QLabel("Shift:")
        filter_label.setStyleSheet("font-size: 10pt;")
        filter_layout.addWidget(filter_label)
        self.bills_shift_filter = QtWidgets.QComboBox()
        self.bills_shift_filter.setMinimumHeight(34)
        self.bills_shift_filter.setStyleSheet("font-size: 10pt;")
        self.bills_shift_filter.currentIndexChanged.connect(self.handle_bills_shift_changed)
        filter_layout.addWidget(self.bills_shift_filter)

        bills_action_layout = QtWidgets.QHBoxLayout()
        bills_action_layout.setSpacing(4)
        filter_layout.addLayout(bills_action_layout)

        def make_bills_action_button(label: str, handler, *, width: int = 84) -> QtWidgets.QPushButton:
            button = QtWidgets.QPushButton(label)
            button.setFixedSize(width, 42)
            button.setStyleSheet(
                "QPushButton {"
                " font-size: 10pt;"
                " min-height: 0px;"
                " padding: 3px 6px;"
                " border: 1px solid #6f6f6f;"
                " border-radius: 0px;"
                " background-color: #2f2f2f;"
                " }"
                "QPushButton:hover { background-color: #3a3a3a; }"
                "QPushButton:pressed { background-color: #262626; }"
            )
            button.clicked.connect(handler)
            return button

        self.close_day_button = make_bills_action_button("Close", self.close_current_day)
        bills_action_layout.addWidget(self.close_day_button)

        self.shift_report_button = make_bills_action_button(
            "End Of Day",
            self.show_selected_shift_report,
            width=108,
        )
        bills_action_layout.addWidget(self.shift_report_button)

        self.backup_button = make_bills_action_button("Backup", self.create_data_backup)
        bills_action_layout.addWidget(self.backup_button)

        self.restore_button = make_bills_action_button("Restore", self.restore_data_backup)
        bills_action_layout.addWidget(self.restore_button)

        self.edit_bill_button = make_bills_action_button("Edit", self.edit_selected_bill)
        bills_action_layout.addWidget(self.edit_bill_button)

        self.reprint_button = make_bills_action_button("Receipt", self.reprint_selected_receipt)
        bills_action_layout.addWidget(self.reprint_button)

        filter_layout.addStretch()

        self.bills_content_layout = QtWidgets.QHBoxLayout()
        self.bills_content_layout.setSpacing(8)
        layout.addLayout(self.bills_content_layout, 1)
        summary_group = QtWidgets.QGroupBox("Shift Summary")
        summary_group.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Maximum,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        summary_group.setStyleSheet(
            "QGroupBox { font-size: 10pt; font-weight: 600; }"
            "QLabel { font-size: 9pt; }"
        )
        summary_layout = QtWidgets.QFormLayout()
        summary_layout.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        summary_layout.setFormAlignment(QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft)
        summary_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
        summary_layout.setRowWrapPolicy(QtWidgets.QFormLayout.RowWrapPolicy.DontWrapRows)
        summary_group.setLayout(summary_layout)
        self.bills_shift_label = QtWidgets.QLabel("-")
        self.bills_opened_label = QtWidgets.QLabel("-")
        self.bills_closed_label = QtWidgets.QLabel("-")
        self.bills_count_label = QtWidgets.QLabel("0")
        self.bills_cash_label = QtWidgets.QLabel(f"{CURRENCY}0.00")
        self.bills_card_label = QtWidgets.QLabel(f"{CURRENCY}0.00")
        self.bills_visa_label = QtWidgets.QLabel(f"{CURRENCY}0.00")
        self.bills_mastercard_label = QtWidgets.QLabel(f"{CURRENCY}0.00")
        self.bills_amex_label = QtWidgets.QLabel(f"{CURRENCY}0.00")
        self.bills_total_label = QtWidgets.QLabel(f"{CURRENCY}0.00")
        summary_widgets = (
            self.bills_shift_label,
            self.bills_opened_label,
            self.bills_closed_label,
            self.bills_count_label,
            self.bills_cash_label,
            self.bills_card_label,
            self.bills_visa_label,
            self.bills_mastercard_label,
            self.bills_amex_label,
            self.bills_total_label,
        )
        for widget in summary_widgets:
            widget.setWordWrap(False)
            widget.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)

        summary_layout.addRow("Viewing Shift", self.bills_shift_label)
        summary_layout.addRow("Transactions", self.bills_count_label)
        summary_layout.addRow("Opened", self.bills_opened_label)
        summary_layout.addRow("Closed", self.bills_closed_label)
        summary_layout.addRow("Cash Total =", self.bills_cash_label)
        summary_layout.addRow("Cards Total =", self.bills_card_label)
        summary_layout.addRow("Visa =", self.bills_visa_label)
        summary_layout.addRow("Mastercard =", self.bills_mastercard_label)
        summary_layout.addRow("Amex =", self.bills_amex_label)
        summary_layout.addRow("TOTAL =", self.bills_total_label)
        self.bills_content_layout.addWidget(summary_group, 0)

        left_panel = QtWidgets.QWidget()
        left_panel.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        left_panel.setMinimumWidth(380)
        left_layout = QtWidgets.QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)
        left_panel.setLayout(left_layout)
        left_title = QtWidgets.QLabel("Bills history")
        left_title.setStyleSheet("font-size: 10pt; font-weight: 600;")
        left_layout.addWidget(left_title)
        self.bills_list = QtWidgets.QListWidget()
        self.bills_list.setMinimumWidth(380)
        self.bills_list.setStyleSheet("font-size: 10pt;")
        self.bills_list.itemSelectionChanged.connect(self.show_selected_bill_details)
        left_layout.addWidget(self.bills_list, 1)

        right_panel = QtWidgets.QWidget()
        right_panel.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        right_panel.setMinimumWidth(380)
        right_layout = QtWidgets.QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)
        right_panel.setLayout(right_layout)
        details_header_layout = QtWidgets.QHBoxLayout()
        details_header_layout.setContentsMargins(0, 0, 0, 0)
        details_title = QtWidgets.QLabel("Bill details")
        details_title.setStyleSheet("font-size: 10pt; font-weight: 600;")
        details_header_layout.addWidget(details_title)
        details_header_layout.addStretch()
        self.bill_status_badge = QtWidgets.QLabel("")
        self.bill_status_badge.setStyleSheet(
            "background-color: #5a4321; color: #ffe7b3; border-radius: 10px; padding: 3px 8px; font-size: 9pt; font-weight: 600;"
        )
        self.bill_status_badge.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Maximum,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.bill_status_badge.hide()
        details_header_layout.addWidget(self.bill_status_badge, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        right_layout.addLayout(details_header_layout)
        self.bill_detail = QtWidgets.QTextEdit()
        self.bill_detail.setReadOnly(True)
        self.bill_detail.setMinimumWidth(380)
        self.bill_detail.setStyleSheet("font-size: 10pt;")
        right_layout.addWidget(self.bill_detail, 1)

        self.bills_content_layout.addWidget(left_panel, 1)
        self.bills_content_layout.addWidget(right_panel, 1)

    def format_shift_report_text(
        self,
        summary: dict[str, object],
        transactions: list[Transaction],
    ) -> str:
        heading = "Shift Report" if summary["is_open"] else "End Of Day Report"
        opened_at = summary["opened_at"]
        closed_at = summary["closed_at"]
        lines = [
            heading,
            f"Shift: #{summary['shift_id']}",
            f"Status: {'Open' if summary['is_open'] else 'Closed'}",
            f"Opened: {opened_at.strftime('%Y-%m-%d %H:%M:%S') if opened_at is not None else '-'}",
            f"Closed: {closed_at.strftime('%Y-%m-%d %H:%M:%S') if closed_at is not None else '-'}",
            f"Transactions: {summary['count']}",
            f"Cash: {CURRENCY}{summary['cash_total']:.2f}",
            f"Card: {CURRENCY}{summary['card_total']:.2f}",
            f"Visa: {CURRENCY}{summary['visa_total']:.2f}",
            f"Mastercard: {CURRENCY}{summary['mastercard_total']:.2f}",
            f"Amex: {CURRENCY}{summary['amex_total']:.2f}",
            f"Total: {CURRENCY}{summary['total']:.2f}",
            "",
            "Payment Breakdown (Newest first)",
        ]
        if not transactions:
            lines.append("No completed payments for this shift.")
            return "\n".join(lines)

        sorted_transactions = sorted(
            transactions,
            key=lambda transaction: transaction.timestamp,
            reverse=True,
        )

        for transaction in sorted_transactions:
            lines.append(
                f"#{transaction.id or '-'}  {transaction.timestamp.strftime('%Y-%m-%d %H:%M:%S')}  {transaction.payment_method}  {CURRENCY}{transaction.total:.2f}"
            )
        return "\n".join(lines).rstrip()

    def show_shift_report_dialog(self, shift_id: int | None = None, title: str | None = None) -> None:
        target_shift_id = shift_id or self.bills_shift_filter.currentData()
        if target_shift_id is None:
            QtWidgets.QMessageBox.information(self, "Bills", "No shift selected.")
            return

        summary = self.inventory.db.get_shift_summary(target_shift_id)
        transactions = self.inventory.db.list_transactions(limit=500, shift_id=target_shift_id)
        dialog_title = title or (
            f"Shift Report - Shift #{target_shift_id}"
            if summary["is_open"]
            else f"End Of Day Report - Shift #{target_shift_id}"
        )

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(dialog_title)
        dialog.resize(720, 680)

        layout = QtWidgets.QVBoxLayout(dialog)
        report = QtWidgets.QTextEdit()
        report.setReadOnly(True)
        report_font = QtGui.QFont("Consolas", 12)
        report_font.setStyleHint(QtGui.QFont.StyleHint.Monospace)
        report.setFont(report_font)
        report.setLineWrapMode(QtWidgets.QTextEdit.LineWrapMode.NoWrap)
        report.setPlainText(self.format_shift_report_text(summary, transactions))
        layout.addWidget(report)

        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)

        dialog.exec()

    def get_selected_bill(self) -> Transaction | None:
        item = self.bills_list.currentItem()
        if item is None:
            return None
        transaction_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if transaction_id is None:
            return None
        return self.inventory.db.get_transaction(transaction_id)

    def show_selected_bill_details(self):
        transaction = self.get_selected_bill()
        if transaction is None:
            self.bill_status_badge.hide()
            self.bill_status_badge.setText("")
            self.bill_detail.setPlainText("No bill selected.")
            return
        if transaction.edited_at is not None:
            self.bill_status_badge.setText(
                f"Edited at {transaction.edited_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            self.bill_status_badge.show()
        else:
            self.bill_status_badge.hide()
            self.bill_status_badge.setText("")
        self.bill_detail.setPlainText(self.format_transaction_text(transaction))

    def reprint_selected_receipt(self):
        transaction = self.get_selected_bill()
        if transaction is None:
            QtWidgets.QMessageBox.information(self, "Bills", "Select a bill first.")
            return
        self.show_receipt_dialog(transaction, title="Receipt")

    def edit_selected_bill(self):
        if not self.check_pin():
            return

        transaction = self.get_selected_bill()
        if transaction is None:
            QtWidgets.QMessageBox.information(self, "Bills", "Select a bill first.")
            return

        edited_transaction = prompt_edit_bill(self, transaction)
        if edited_transaction is None:
            return

        try:
            self.inventory.db.update_transaction(edited_transaction)
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(self, "Edit Bill", str(exc))
            return

        self.refresh_bills(refresh_shift_filter=False)
        self.refresh_reports(refresh_shift_filter=False)
        self.show_selected_bill_details()

    def show_selected_shift_report(self):
        shift_id = self.bills_shift_filter.currentData()
        if shift_id is None:
            QtWidgets.QMessageBox.information(self, "Bills", "Select a shift first.")
            return
        self.show_shift_report_dialog(shift_id)

    def get_active_database(self):
        return getattr(self.inventory, "db", None) or getattr(self.cart, "db", None)

    def create_automatic_backup(self) -> str | None:
        db = self.get_active_database()
        if db is None:
            return "Database is not available."
        try:
            db.backups.create_timestamped_backup(kind="auto")
        except Exception as exc:
            return str(exc)
        return None

    def build_backup_choice_label(self, backup_path) -> str:
        name = backup_path.name
        parent_name = backup_path.parent.name.lower()
        if parent_name == "manual":
            return f"Manual | {name}"
        if parent_name == "auto":
            return f"Auto | {name}"
        if ".pre_restore." in name:
            return f"{name} (safety backup)"
        return name

    def create_data_backup(self):
        if not self.check_pin():
            return

        db = self.get_active_database()
        if db is None:
            QtWidgets.QMessageBox.warning(self, "Backup Data", "Database is not available.")
            return

        try:
            backup_path = db.backups.create_timestamped_backup(kind="manual")
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Backup Data", f"Backup failed.\n\n{exc}")
            return

        QtWidgets.QMessageBox.information(
            self,
            "Backup Data",
            f"Backup created successfully.\n\n{backup_path.name}",
        )

    def restore_data_backup(self):
        if not self.check_pin():
            return

        db = self.get_active_database()
        if db is None:
            QtWidgets.QMessageBox.warning(self, "Restore Backup", "Database is not available.")
            return

        backups = db.backups.list_backups()
        if not backups:
            QtWidgets.QMessageBox.information(self, "Restore Backup", "No backups are available yet.")
            return

        backup_labels = [self.build_backup_choice_label(path) for path in backups]
        selected_label, ok = QtWidgets.QInputDialog.getItem(
            self,
            "Restore Backup",
            "Choose a backup to restore:",
            backup_labels,
            current=0,
            editable=False,
        )
        if not ok:
            return

        selected_index = backup_labels.index(selected_label)
        selected_backup = backups[selected_index]

        reply = QtWidgets.QMessageBox.question(
            self,
            "Restore Backup",
            (
                f"Restore backup '{selected_backup.name}'?\n\n"
                "This will replace the current live till data. "
                "A safety backup of the current database will be created first."
            ),
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        try:
            safety_backup = db.backups.restore_from_backup(selected_backup)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Restore Backup", f"Restore failed.\n\n{exc}")
            return

        self.cart.clear()
        self.refresh_cart()
        self.refresh_products()
        self.refresh_bills()
        self.refresh_reports()
        QtWidgets.QMessageBox.information(
            self,
            "Restore Backup",
            (
                f"Restored {selected_backup.name}.\n\n"
                f"Safety backup saved as {safety_backup.name}."
            ),
        )

    def handle_bills_shift_changed(self):
        self.refresh_bills(refresh_shift_filter=False)

    def set_bills_shift_filter(self, shift_id: int | None):
        if shift_id is None:
            return
        for index in range(self.bills_shift_filter.count()):
            if self.bills_shift_filter.itemData(index) == shift_id:
                self.bills_shift_filter.setCurrentIndex(index)
                return

    def refresh_bills_shift_filter(self, selected_shift_id: int | None = None):
        current_db_identity = id(self.inventory.db)
        open_shift = self.inventory.db.get_or_create_open_shift()
        if selected_shift_id is None:
            if (
                self.bills_shift_filter.count()
                and getattr(self, "_bills_shift_filter_db_identity", None) == current_db_identity
            ):
                selected_shift_id = self.bills_shift_filter.currentData()
            else:
                selected_shift_id = open_shift.id
        shifts = self.inventory.db.list_shifts(limit=100)

        self.bills_shift_filter.blockSignals(True)
        self.bills_shift_filter.clear()
        for shift in shifts:
            status = "Open" if shift.is_open else "Closed"
            label = f"Shift #{shift.id} ({status})"
            if shift.closed_at is not None:
                label += f" - {shift.opened_at.strftime('%d/%m %H:%M')} to {shift.closed_at.strftime('%d/%m %H:%M')}"
            else:
                label += f" - opened {shift.opened_at.strftime('%d/%m %H:%M')}"
            self.bills_shift_filter.addItem(label, shift.id)

        target_shift_id = selected_shift_id
        available_shift_ids = {self.bills_shift_filter.itemData(index) for index in range(self.bills_shift_filter.count())}
        if target_shift_id not in available_shift_ids:
            target_shift_id = open_shift.id

        for index in range(self.bills_shift_filter.count()):
            if self.bills_shift_filter.itemData(index) == target_shift_id:
                self.bills_shift_filter.setCurrentIndex(index)
                break
        self.bills_shift_filter.blockSignals(False)
        self._bills_shift_filter_db_identity = current_db_identity

    def close_current_day(self):
        if not self.check_pin():
            return

        current_summary = self.inventory.db.get_open_shift_summary()
        reply = QtWidgets.QMessageBox.question(
            self,
            "Close Day",
            (
                f"Close current shift #{current_summary['shift_id']}?\n\n"
                f"Transactions: {current_summary['count']}\n"
                f"Total: {CURRENCY}{current_summary['total']:.2f}\n"
                f"Cash: {CURRENCY}{current_summary['cash_total']:.2f}\n"
                f"Card: {CURRENCY}{current_summary['card_total']:.2f}\n"
                f"Visa: {CURRENCY}{current_summary['visa_total']:.2f}\n"
                f"Mastercard: {CURRENCY}{current_summary['mastercard_total']:.2f}\n"
                f"Amex: {CURRENCY}{current_summary['amex_total']:.2f}"
            ),
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        closed_shift, new_shift = self.inventory.db.close_current_shift()
        backup_error = self.create_automatic_backup()
        self.refresh_bills(selected_shift_id=new_shift.id)
        self.refresh_reports()
        self.show_shift_report_dialog(
            closed_shift.id,
            title=f"End Of Day Report - Shift #{closed_shift.id}",
        )
        if backup_error is None:
            QtWidgets.QMessageBox.information(
                self,
                "Close Day",
                (
                    f"Closed shift #{closed_shift.id}.\n"
                    f"New shift #{new_shift.id} is now open."
                ),
            )
        else:
            QtWidgets.QMessageBox.warning(
                self,
                "Close Day",
                (
                    f"Closed shift #{closed_shift.id}.\n"
                    f"New shift #{new_shift.id} is now open.\n\n"
                    f"Automatic close-day backup failed.\n\n{backup_error}"
                ),
            )

    def refresh_bills(
        self,
        selected_shift_id: int | None = None,
        refresh_shift_filter: bool = True,
    ):
        if refresh_shift_filter:
            self.refresh_bills_shift_filter(selected_shift_id=selected_shift_id)

        shift_id = selected_shift_id
        if shift_id is None:
            shift_id = self.bills_shift_filter.currentData()
        if shift_id is None:
            shift_id = self.inventory.db.get_or_create_open_shift().id

        transactions = self.inventory.db.list_transactions(limit=200, shift_id=shift_id)
        summary = self.inventory.db.get_shift_summary(shift_id)

        status = "Open" if summary["is_open"] else "Closed"
        self.bills_shift_label.setText(f"#{summary['shift_id']} ({status})")
        if summary["opened_at"] is not None:
            self.bills_opened_label.setText(summary["opened_at"].strftime("%d/%m %H:%M"))
        else:
            self.bills_opened_label.setText("-")
        if summary["closed_at"] is not None:
            self.bills_closed_label.setText(summary["closed_at"].strftime("%d/%m %H:%M"))
        else:
            self.bills_closed_label.setText("-")
        self.bills_count_label.setText(str(summary["count"]))
        self.bills_cash_label.setText(f"{CURRENCY}{summary['cash_total']:.2f}")
        self.bills_card_label.setText(f"{CURRENCY}{summary['card_total']:.2f}")
        self.bills_visa_label.setText(f"{CURRENCY}{summary['visa_total']:.2f}")
        self.bills_mastercard_label.setText(f"{CURRENCY}{summary['mastercard_total']:.2f}")
        self.bills_amex_label.setText(f"{CURRENCY}{summary['amex_total']:.2f}")
        self.bills_total_label.setText(f"{CURRENCY}{summary['total']:.2f}")

        selected_id = None
        current_item = self.bills_list.currentItem()
        if current_item is not None:
            selected_id = current_item.data(QtCore.Qt.ItemDataRole.UserRole)

        self.bills_list.clear()
        for transaction in transactions:
            edited_marker = "EDITED  " if transaction.edited_at is not None else ""
            item = QtWidgets.QListWidgetItem(
                f"{edited_marker}#{transaction.id}  S{transaction.shift_id or '-'}  {transaction.timestamp.strftime('%d/%m %H:%M')}  {transaction.payment_method}  {CURRENCY}{transaction.total:.2f}"
            )
            item.setData(QtCore.Qt.ItemDataRole.UserRole, transaction.id)
            if transaction.edited_at is not None:
                item.setBackground(QtGui.QColor("#5a4321"))
                item.setForeground(QtGui.QColor("#ffe7b3"))
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                item.setToolTip(
                    f"Edited bill at {transaction.edited_at.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            self.bills_list.addItem(item)

        if self.bills_list.count() == 0:
            self.bill_status_badge.hide()
            self.bill_status_badge.setText("")
            self.bill_detail.setPlainText("No completed bills yet.")
            return

        selected_row = 0
        if selected_id is not None:
            for index in range(self.bills_list.count()):
                if self.bills_list.item(index).data(QtCore.Qt.ItemDataRole.UserRole) == selected_id:
                    selected_row = index
                    break
        self.bills_list.setCurrentRow(selected_row)