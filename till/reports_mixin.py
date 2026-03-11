"""Reports tab UI and item sales summaries for the till."""

from __future__ import annotations

import datetime

from PyQt6 import QtCore, QtWidgets

from .categories import format_display_name

CURRENCY = "£"


class ReportsMixin:
    REPORTS_HEADERS = ("Item", "Category", "Subcategory", "Qty Sold", "Revenue")

    def build_reports_tab(self) -> None:
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        self.reports_tab.setLayout(layout)
        group_style = (
            "QGroupBox { font-size: 10pt; font-weight: 600; }"
            "QLabel { font-size: 9pt; }"
        )

        top_layout = QtWidgets.QHBoxLayout()
        top_layout.setSpacing(8)
        layout.addLayout(top_layout)

        sessions_group = QtWidgets.QGroupBox("Sessions")
        sessions_group.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Maximum,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        sessions_group.setStyleSheet(group_style)
        sessions_layout = QtWidgets.QVBoxLayout()
        sessions_group.setLayout(sessions_layout)
        sessions_layout.addWidget(
            QtWidgets.QLabel("Select one or more sessions, or leave empty for the current open session.")
        )
        self.reports_shift_list = QtWidgets.QListWidget()
        self.reports_shift_list.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.reports_shift_list.setMinimumWidth(300)
        self.reports_shift_list.setMinimumHeight(150)
        self.reports_shift_list.setStyleSheet("font-size: 10pt;")
        self.reports_shift_list.itemSelectionChanged.connect(self.handle_reports_filters_changed)
        sessions_layout.addWidget(self.reports_shift_list, 1)
        top_layout.addWidget(sessions_group, 0)

        controls_group = QtWidgets.QGroupBox("Filters")
        controls_group.setStyleSheet(group_style)
        controls_layout = QtWidgets.QGridLayout()
        controls_layout.setHorizontalSpacing(8)
        controls_layout.setVerticalSpacing(8)
        controls_group.setLayout(controls_layout)

        self.reports_from_checkbox = QtWidgets.QCheckBox("From")
        self.reports_from_checkbox.setStyleSheet("font-size: 10pt;")
        self.reports_from_checkbox.toggled.connect(self.handle_reports_from_toggled)
        controls_layout.addWidget(self.reports_from_checkbox, 0, 0)

        self.reports_from_datetime = QtWidgets.QDateTimeEdit(QtCore.QDateTime.currentDateTime())
        self.reports_from_datetime.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.reports_from_datetime.setCalendarPopup(True)
        self.reports_from_datetime.setEnabled(False)
        self.reports_from_datetime.setMinimumHeight(34)
        self.reports_from_datetime.setStyleSheet("font-size: 10pt;")
        self.reports_from_datetime.dateTimeChanged.connect(self.handle_reports_filters_changed)
        controls_layout.addWidget(self.reports_from_datetime, 0, 1)

        self.reports_to_checkbox = QtWidgets.QCheckBox("To")
        self.reports_to_checkbox.setStyleSheet("font-size: 10pt;")
        self.reports_to_checkbox.toggled.connect(self.handle_reports_to_toggled)
        controls_layout.addWidget(self.reports_to_checkbox, 1, 0)

        self.reports_to_datetime = QtWidgets.QDateTimeEdit(QtCore.QDateTime.currentDateTime())
        self.reports_to_datetime.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.reports_to_datetime.setCalendarPopup(True)
        self.reports_to_datetime.setEnabled(False)
        self.reports_to_datetime.setMinimumHeight(34)
        self.reports_to_datetime.setStyleSheet("font-size: 10pt;")
        self.reports_to_datetime.dateTimeChanged.connect(self.handle_reports_filters_changed)
        controls_layout.addWidget(self.reports_to_datetime, 1, 1)

        self.reports_clear_filters_button = QtWidgets.QPushButton("Clear Filters")
        self.reports_clear_filters_button.setMinimumHeight(38)
        self.reports_clear_filters_button.setStyleSheet("font-size: 10pt;")
        self.reports_clear_filters_button.clicked.connect(self.clear_reports_filters)
        controls_layout.addWidget(self.reports_clear_filters_button, 2, 0, 1, 2)

        top_layout.addWidget(controls_group, 0)

        summary_group = QtWidgets.QGroupBox("Summary")
        summary_group.setStyleSheet(group_style)
        summary_layout = QtWidgets.QFormLayout()
        summary_group.setLayout(summary_layout)
        self.reports_sessions_label = QtWidgets.QLabel("-")
        self.reports_date_range_label = QtWidgets.QLabel("Any time")
        self.reports_item_count_label = QtWidgets.QLabel("0")
        self.reports_units_sold_label = QtWidgets.QLabel("0")
        self.reports_revenue_label = QtWidgets.QLabel(f"{CURRENCY}0.00")
        summary_layout.addRow("Sessions", self.reports_sessions_label)
        summary_layout.addRow("Time Range", self.reports_date_range_label)
        summary_layout.addRow("Items", self.reports_item_count_label)
        summary_layout.addRow("Units Sold", self.reports_units_sold_label)
        summary_layout.addRow("Revenue", self.reports_revenue_label)
        top_layout.addWidget(summary_group, 1)

        self.reports_table = QtWidgets.QTableWidget()
        self.reports_table.setColumnCount(len(self.REPORTS_HEADERS))
        self.reports_table.setHorizontalHeaderLabels(list(self.REPORTS_HEADERS))
        self.reports_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.reports_table.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        self.reports_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.reports_table.setAlternatingRowColors(True)
        self.reports_table.setShowGrid(False)
        self.reports_table.setStyleSheet("font-size: 10pt;")
        self.reports_table.verticalHeader().setVisible(False)
        header = self.reports_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(110)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.reports_table, 1)

    def build_reports_shift_label(self, shift) -> str:
        status = "Open" if shift.is_open else "Closed"
        if shift.closed_at is not None:
            return (
                f"Session #{shift.id} ({status}) - "
                f"{shift.opened_at.strftime('%d/%m %H:%M')} to {shift.closed_at.strftime('%d/%m %H:%M')}"
            )
        return f"Session #{shift.id} ({status}) - opened {shift.opened_at.strftime('%d/%m %H:%M')}"

    def refresh_reports_shift_list(self) -> None:
        current_db_identity = id(self.inventory.db)
        selected_shift_ids: set[int] = set()
        if getattr(self, "_reports_shift_list_db_identity", None) == current_db_identity:
            selected_shift_ids = set(self.get_selected_reports_shift_ids())

        shifts = self.inventory.db.list_shifts(limit=100)
        self.reports_shift_list.blockSignals(True)
        self.reports_shift_list.clear()
        for shift in shifts:
            item = QtWidgets.QListWidgetItem(self.build_reports_shift_label(shift))
            item.setData(QtCore.Qt.ItemDataRole.UserRole, shift.id)
            self.reports_shift_list.addItem(item)
            if shift.id in selected_shift_ids:
                item.setSelected(True)
        self.reports_shift_list.blockSignals(False)
        self._reports_shift_list_db_identity = current_db_identity

    def get_selected_reports_shift_ids(self) -> list[int]:
        return [
            int(item.data(QtCore.Qt.ItemDataRole.UserRole))
            for item in self.reports_shift_list.selectedItems()
            if item.data(QtCore.Qt.ItemDataRole.UserRole) is not None
        ]

    def handle_reports_from_toggled(self, checked: bool) -> None:
        self.reports_from_datetime.setEnabled(checked)
        self.refresh_reports(refresh_shift_filter=False)

    def handle_reports_to_toggled(self, checked: bool) -> None:
        self.reports_to_datetime.setEnabled(checked)
        self.refresh_reports(refresh_shift_filter=False)

    def handle_reports_filters_changed(self, *_args) -> None:
        self.refresh_reports(refresh_shift_filter=False)

    def clear_reports_filters(self) -> None:
        self.reports_shift_list.blockSignals(True)
        self.reports_shift_list.clearSelection()
        self.reports_shift_list.blockSignals(False)
        self.reports_from_checkbox.blockSignals(True)
        self.reports_to_checkbox.blockSignals(True)
        self.reports_from_checkbox.setChecked(False)
        self.reports_to_checkbox.setChecked(False)
        self.reports_from_checkbox.blockSignals(False)
        self.reports_to_checkbox.blockSignals(False)
        self.reports_from_datetime.setEnabled(False)
        self.reports_to_datetime.setEnabled(False)
        now = QtCore.QDateTime.currentDateTime()
        self.reports_from_datetime.setDateTime(now)
        self.reports_to_datetime.setDateTime(now)
        self.refresh_reports(refresh_shift_filter=False)

    def get_reports_datetime_filters(self) -> tuple[datetime.datetime | None, datetime.datetime | None]:
        start_at = (
            self.reports_from_datetime.dateTime().toPyDateTime()
            if self.reports_from_checkbox.isChecked()
            else None
        )
        end_at = (
            self.reports_to_datetime.dateTime().toPyDateTime()
            if self.reports_to_checkbox.isChecked()
            else None
        )
        return start_at, end_at

    def describe_reports_sessions(self, shift_ids: list[int], *, has_date_filter: bool) -> str:
        if shift_ids:
            if len(shift_ids) == 1:
                return f"1 selected session (#{shift_ids[0]})"
            return f"{len(shift_ids)} selected sessions"
        if has_date_filter:
            return "All sessions in selected time range"
        open_shift = self.inventory.db.get_or_create_open_shift()
        return f"Current open session #{open_shift.id}"

    def format_reports_date_range(
        self,
        start_at: datetime.datetime | None,
        end_at: datetime.datetime | None,
    ) -> str:
        if start_at is None and end_at is None:
            return "Any time"
        if start_at is not None and end_at is not None:
            return f"{start_at.strftime('%d/%m/%Y %H:%M')} to {end_at.strftime('%d/%m/%Y %H:%M')}"
        if start_at is not None:
            return f"From {start_at.strftime('%d/%m/%Y %H:%M')}"
        return f"Up to {end_at.strftime('%d/%m/%Y %H:%M')}"

    def refresh_reports(self, *, refresh_shift_filter: bool = True) -> None:
        table = getattr(self, "reports_table", None)
        if table is None:
            return
        if refresh_shift_filter:
            self.refresh_reports_shift_list()

        selected_shift_ids = self.get_selected_reports_shift_ids()
        start_at, end_at = self.get_reports_datetime_filters()
        has_date_filter = start_at is not None or end_at is not None

        effective_shift_ids: list[int] | None = selected_shift_ids or None
        if effective_shift_ids is None and not has_date_filter:
            effective_shift_ids = [self.inventory.db.get_or_create_open_shift().id]

        item_sales = self.inventory.db.list_item_sales(
            shift_ids=effective_shift_ids,
            start_at=start_at,
            end_at=end_at,
        )

        table.clearContents()
        table.setRowCount(len(item_sales))
        total_units = 0
        total_revenue = 0.0
        for row_index, item_sale in enumerate(item_sales):
            total_units += item_sale.quantity_sold
            total_revenue += item_sale.revenue
            values = (
                item_sale.product_name,
                format_display_name(item_sale.category),
                format_display_name(item_sale.sub_category),
                str(item_sale.quantity_sold),
                f"{CURRENCY}{item_sale.revenue:.2f}",
            )
            for column, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                table.setItem(row_index, column, item)

        self.reports_sessions_label.setText(
            self.describe_reports_sessions(selected_shift_ids, has_date_filter=has_date_filter)
        )
        self.reports_date_range_label.setText(self.format_reports_date_range(start_at, end_at))
        self.reports_item_count_label.setText(str(len(item_sales)))
        self.reports_units_sold_label.setText(str(total_units))
        self.reports_revenue_label.setText(f"{CURRENCY}{total_revenue:.2f}")
