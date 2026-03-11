"""Product Details tab UI for the till."""

from __future__ import annotations

from PyQt6 import QtCore, QtWidgets

from .categories import format_display_name, resolve_category_name, resolve_subcategory_name
from .models import Product

CURRENCY = "£"


class ProductDetailsMixin:
    PRODUCT_DETAILS_HEADERS = ("Name", "Price", "Category", "Subcategory")

    def build_product_details_tab(self) -> None:
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        self.product_details_tab.setLayout(layout)

        search_layout = QtWidgets.QHBoxLayout()
        search_layout.setSpacing(8)
        layout.addLayout(search_layout)

        search_label = QtWidgets.QLabel("Search")
        search_label.setMinimumWidth(64)
        search_layout.addWidget(search_label)

        self.product_details_search = QtWidgets.QLineEdit()
        self.product_details_search.setPlaceholderText("Search product, price, category, or subcategory")
        self.product_details_search.setClearButtonEnabled(True)
        self.product_details_search.setMinimumHeight(48)
        self.product_details_search.textChanged.connect(self.handle_product_details_search_changed)
        search_layout.addWidget(self.product_details_search, 1)

        self.product_details_count_label = QtWidgets.QLabel("0 products")
        self.product_details_count_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self.product_details_count_label.setMinimumWidth(160)
        search_layout.addWidget(self.product_details_count_label)

        action_layout = QtWidgets.QHBoxLayout()
        action_layout.setSpacing(8)
        layout.addLayout(action_layout)

        self.product_details_add_button = QtWidgets.QPushButton("Add")
        self.product_details_add_button.setMinimumHeight(48)
        self.product_details_add_button.clicked.connect(self.add_product_dialog)
        action_layout.addWidget(self.product_details_add_button)

        self.product_details_edit_button = QtWidgets.QPushButton("Edit")
        self.product_details_edit_button.setMinimumHeight(48)
        self.product_details_edit_button.clicked.connect(self.edit_product_from_details)
        action_layout.addWidget(self.product_details_edit_button)

        self.product_details_delete_button = QtWidgets.QPushButton("Delete")
        self.product_details_delete_button.setMinimumHeight(48)
        self.product_details_delete_button.clicked.connect(self.delete_product_from_details)
        action_layout.addWidget(self.product_details_delete_button)

        action_layout.addStretch()

        self.product_details_table = QtWidgets.QTableWidget()
        self.product_details_table.setColumnCount(len(self.PRODUCT_DETAILS_HEADERS))
        self.product_details_table.setHorizontalHeaderLabels(list(self.PRODUCT_DETAILS_HEADERS))
        self.product_details_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.product_details_table.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        self.product_details_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.product_details_table.setAlternatingRowColors(True)
        self.product_details_table.setSortingEnabled(False)
        self.product_details_table.setShowGrid(False)
        self.product_details_table.setWordWrap(False)
        self.product_details_table.setHorizontalScrollMode(
            QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        self.product_details_table.setVerticalScrollMode(
            QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        vertical_header = self.product_details_table.verticalHeader()
        vertical_header.setVisible(False)
        vertical_header.setDefaultSectionSize(46)
        header = self.product_details_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setMinimumSectionSize(120)
        header.setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        header.setFixedHeight(42)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.product_details_table.itemSelectionChanged.connect(self.handle_product_details_selection_changed)
        layout.addWidget(self.product_details_table, 1)

        self.product_details_selected_product_id: int | None = None

    def handle_product_details_search_changed(self, _text: str) -> None:
        self.refresh_product_details()

    def handle_product_details_selection_changed(self) -> None:
        self.product_details_selected_product_id = self.get_selected_product_details_id()

    def get_selected_product_details_id(self) -> int | None:
        table = getattr(self, "product_details_table", None)
        if table is None:
            return None
        selected_items = table.selectedItems()
        if not selected_items:
            return None
        return selected_items[0].data(QtCore.Qt.ItemDataRole.UserRole)

    def get_selected_product_details_product(self) -> Product | None:
        product_id = self.get_selected_product_details_id()
        if product_id is None:
            return None
        return self.get_product_by_id(product_id)

    def refresh_product_details(self) -> None:
        table = getattr(self, "product_details_table", None)
        if table is None:
            return

        selected_product_id = self.product_details_selected_product_id
        all_products = sorted(
            self.inventory.list_products(),
            key=lambda product: (
                (product.category or "").lower(),
                (product.sub_category or "").lower(),
                product.name.lower(),
                product.id or 0,
            ),
        )
        search_query = self.product_details_search.text().strip().lower()
        products = [
            product
            for product in all_products
            if self.product_matches_details_search(product, search_query)
        ]

        if search_query:
            self.product_details_count_label.setText(
                f"Showing {len(products)} of {len(all_products)} products"
            )
        elif len(all_products) == 1:
            self.product_details_count_label.setText("1 product")
        else:
            self.product_details_count_label.setText(f"{len(all_products)} products")

        table.setRowCount(len(products))
        for row, product in enumerate(products):
            category = self.resolve_product_details_category(product)
            subcategory = self.resolve_product_details_subcategory(product, category)
            values = (
                product.name,
                f"{CURRENCY}{product.price:.2f}",
                category,
                subcategory,
            )
            for column, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                item.setData(QtCore.Qt.ItemDataRole.UserRole, product.id)
                table.setItem(row, column, item)

        table.clearSelection()
        self.product_details_selected_product_id = None
        if selected_product_id is not None:
            for row in range(table.rowCount()):
                item = table.item(row, 0)
                if item is not None and item.data(QtCore.Qt.ItemDataRole.UserRole) == selected_product_id:
                    table.selectRow(row)
                    break

    def product_matches_details_search(self, product: Product, search_query: str) -> bool:
        if not search_query:
            return True
        category = self.resolve_product_details_category(product)
        subcategory = self.resolve_product_details_subcategory(product, category)
        haystacks = (
            product.name,
            category,
            subcategory,
            f"{product.price:.2f}",
            f"{CURRENCY}{product.price:.2f}",
        )
        return any(search_query in (value or "").lower() for value in haystacks)

    def resolve_product_details_category(self, product) -> str:
        return format_display_name(resolve_category_name(self.categories, product.category))

    def resolve_product_details_subcategory(self, product, category: str) -> str:
        return format_display_name(
            resolve_subcategory_name(self.subcategory_map, category, product.sub_category)
        )

    def edit_product_from_details(self) -> None:
        if not self.check_pin():
            return
        product = self.get_selected_product_details_product()
        if product is None:
            QtWidgets.QMessageBox.information(
                self,
                "Edit product",
                "Select a product in Product Details first.",
            )
            return
        self.edit_product(product)

    def delete_product_from_details(self) -> None:
        if not self.check_pin():
            return
        product = self.get_selected_product_details_product()
        if product is None:
            QtWidgets.QMessageBox.information(
                self,
                "Delete product",
                "Select a product in Product Details first.",
            )
            return
        self.delete_product(product)