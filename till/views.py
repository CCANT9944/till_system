"""PyQt6 user interface for the till."""

from PyQt6 import QtWidgets, QtCore, QtGui
from .bills_mixin import BillsMixin
from .app_settings import load_manager_pin
from .controller import InventoryController, CartController
from .db import close_db
from .models import Product, Transaction
from .product_details_mixin import ProductDetailsMixin
from .color_presets import get_preset_color_value, load_color_presets, save_color_presets
from .color_preset_dialog import edit_color_presets_dialog
from .categories import (
    category_requires_subcategory,
    format_display_name,
    get_subcategories_for_category,
    load_category_config,
    names_match,
    resolve_category_name,
    resolve_subcategory_name,
    save_category_config,
)
from .category_editor_dialog import edit_categories_dialog
from .grid_layout import GRID_LAYOUT_PRESETS, load_grid_layout, save_grid_layout
from .button_rows import clear_layout_widgets, rebuild_toggle_button_row, sync_exclusive_button_row
from .dialog_helpers import choose_grid_layout_dialog, choose_product_dialog, request_pin
from .grid_reorder_dialog import show_grid_reorder_dialog
from .grid_widgets import PRODUCT_TILE_SIZE, resolve_product_grid_positions
from .manager_dialog import show_manager_dialog
from .payments import CHECKOUT_PAYMENT_METHODS
from .product_dialogs import prompt_edit_product, prompt_new_product

# currency symbol used throughout UI
CURRENCY = "£"


class MainWindow(QtWidgets.QMainWindow, BillsMixin, ProductDetailsMixin):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Till System")
        self.resize(1080, 660)
        # make UI elements larger for touch screens
        base_font = self.font()
        base_font.setPointSize(12)
        self.setFont(base_font)
        self.setStyleSheet(
            "QPushButton { min-height: 40px; font-size: 14pt; border-radius: 5px; padding: 8px; }"
            "QPushButton:checked { background-color: #4caf50; color: white; }"
            "QScrollArea { background: transparent; }"
            "QLabel { font-size: 14pt; }"
            "QTabBar::tab { min-width: 150px; min-height: 52px; font-size: 14pt; padding: 8px 18px; }"
        )

        self.inventory = InventoryController()
        self.cart = CartController(db=self.inventory.db)

        # basic UI layout
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root_layout = QtWidgets.QVBoxLayout()
        central.setLayout(root_layout)
        self.main_tabs = QtWidgets.QTabWidget()
        root_layout.addWidget(self.main_tabs)

        self.till_tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        self.till_tab.setLayout(layout)
        self.main_tabs.addTab(self.till_tab, "Till")

        self.bills_tab = QtWidgets.QWidget()
        self.main_tabs.addTab(self.bills_tab, "Bills")

        self.product_details_tab = QtWidgets.QWidget()
        self.main_tabs.addTab(self.product_details_tab, "Product Details")

        # category selector buttons
        self.categories, self.subcategory_map = load_category_config()
        self.category_color_presets, self.subcategory_color_presets = load_color_presets()
        self.grid_columns, self.grid_rows = load_grid_layout()
        self.category_buttons: dict[str, QtWidgets.QPushButton] = {}
        self.subcategory_buttons: dict[str, QtWidgets.QPushButton] = {}
        self.current_category: str | None = None
        self.current_subcategory: str | None = None

        self.cat_widget = QtWidgets.QWidget()
        self.cat_layout = QtWidgets.QHBoxLayout()
        self.cat_layout.setContentsMargins(0, 0, 0, 0)
        self.cat_layout.setSpacing(8)
        self.cat_widget.setLayout(self.cat_layout)
        layout.addWidget(self.cat_widget)

        self.subcat_widget = QtWidgets.QWidget()
        self.subcat_layout = QtWidgets.QHBoxLayout()
        self.subcat_layout.setContentsMargins(0, 0, 0, 0)
        self.subcat_layout.setSpacing(8)
        self.subcat_widget.setLayout(self.subcat_layout)
        self.subcat_widget.setVisible(False)
        layout.addWidget(self.subcat_widget)

        # area to display product buttons
        split_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(split_layout)

        self.product_area = QtWidgets.QScrollArea()
        self.product_area.setWidgetResizable(True)
        self.product_container = QtWidgets.QWidget()
        self.product_layout = QtWidgets.QGridLayout()
        self.product_layout.setContentsMargins(0, 0, 0, 0)
        self.product_layout.setSpacing(8)
        self.product_layout.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft
        )
        self.product_container.setLayout(self.product_layout)
        self.product_area.setWidget(self.product_container)
        split_layout.addWidget(self.product_area, 3)

        self.product_buttons: dict[int, QtWidgets.QPushButton] = {}
        self.product_colors: dict[int, str] = {}
        self.products_per_row = self.grid_columns
        self.apply_grid_layout_settings()

        # button group to make product buttons exclusive
        self.product_button_group = QtWidgets.QButtonGroup()
        self.product_button_group.setExclusive(True)
        self.product_button_group.buttonClicked.connect(
            lambda btn: self.select_product(self.product_button_group.id(btn), True)
        )
        self.selected_product_id: int | None = None

        # cart area on right
        cart_widget = QtWidgets.QWidget()
        cart_layout = QtWidgets.QVBoxLayout()
        cart_widget.setLayout(cart_layout)
        self.cart_list = QtWidgets.QListWidget()
        cart_layout.addWidget(self.cart_list)
        self.total_label = QtWidgets.QLabel(f"Total: {CURRENCY}0.00")
        cart_layout.addWidget(self.total_label)
        split_layout.addWidget(cart_widget, 1)

        button_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(button_layout)

        # manager dialog entry point
        manager_button = QtWidgets.QPushButton("Manager")
        manager_button.clicked.connect(self.open_manager_dialog)
        button_layout.addWidget(manager_button)

        to_cart_button = QtWidgets.QPushButton("Add to cart")
        to_cart_button.clicked.connect(self.add_selected_to_cart)
        button_layout.addWidget(to_cart_button)

        remove_button = QtWidgets.QPushButton("Remove from cart")
        remove_button.clicked.connect(self.remove_selected_from_cart)
        button_layout.addWidget(remove_button)

        checkout_button = QtWidgets.QPushButton("Checkout")
        checkout_button.clicked.connect(self.perform_checkout)
        button_layout.addWidget(checkout_button)

        self.build_bills_tab()
        self.build_product_details_tab()
        self.rebuild_category_buttons()
        self.update_subcategories(None)

        self.refresh_products()
        self.refresh_bills()

    def apply_grid_layout_settings(self):
        self.products_per_row = self.grid_columns
        horizontal_spacing = max(self.product_layout.horizontalSpacing(), 0)
        vertical_spacing = max(self.product_layout.verticalSpacing(), 0)
        min_width = (self.grid_columns * PRODUCT_TILE_SIZE) + ((self.grid_columns - 1) * horizontal_spacing) + 4
        min_height = (self.grid_rows * PRODUCT_TILE_SIZE) + ((self.grid_rows - 1) * vertical_spacing) + 4
        self.product_container.setMinimumSize(min_width, min_height)

    def refresh_products(self):
        self.refresh_product_details()
        # clear existing widgets and mappings
        clear_layout_widgets(self.product_layout)
        self.product_buttons.clear()
        self.product_colors.clear()
        self.selected_product_id = None
        # require both category and subcategory to show items
        if not self.current_category:
            lbl = QtWidgets.QLabel("<select category to see items>")
            self.product_layout.addWidget(lbl, 0, 0)
            return
        if category_requires_subcategory(self.subcategory_map, self.current_category) and not self.current_subcategory:
            lbl = QtWidgets.QLabel("<select subcategory to see items>")
            self.product_layout.addWidget(lbl, 0, 0)
            return
        visible_products = self.get_visible_products()
        for p, row, col in resolve_product_grid_positions(visible_products, self.products_per_row):
            btn = QtWidgets.QPushButton(
                f"{p.name}\n{CURRENCY}{p.price:.2f}"
            )
            btn.setCheckable(True)
            btn.setFixedSize(PRODUCT_TILE_SIZE, PRODUCT_TILE_SIZE)
            # configure basic style; white-space not supported by QPushButton
            style = "text-align: center; font-size: 10pt;"
            if p.color:
                style += f" background-color: {p.color};"
            btn.setStyleSheet(style)
            # add with id for selection
            self.product_button_group.addButton(btn, p.id)
            self.product_buttons[p.id] = btn
            self.product_colors[p.id] = p.color or ""
            btn.setProperty("product_font_size", p.font_size or 10)
            self.apply_button_style(p.id, selected=False)
            self.product_layout.addWidget(btn, row, col)

    def get_visible_products(self) -> list[Product]:
        if not self.current_category:
            return []
        selected_category = resolve_category_name(self.categories, self.current_category)
        requires_subcategory = category_requires_subcategory(self.subcategory_map, selected_category)
        selected_subcategory = resolve_subcategory_name(
            self.subcategory_map,
            selected_category,
            self.current_subcategory,
        )
        products: list[Product] = []
        for product in self.inventory.list_products():
            if not names_match(resolve_category_name(self.categories, product.category), selected_category):
                continue
            if requires_subcategory and not names_match(
                resolve_subcategory_name(self.subcategory_map, selected_category, product.sub_category),
                selected_subcategory,
            ):
                continue
            products.append(product)
        return sorted(
            products,
            key=lambda product: (
                0
                if product.tile_row is not None and product.tile_column is not None
                else 1,
                product.tile_row if product.tile_row is not None else 10**9,
                product.tile_column if product.tile_column is not None else 10**9,
                product.tile_order or 0,
                product.id or 0,
            ),
        )

    def rebuild_category_buttons(self):
        self.category_buttons = rebuild_toggle_button_row(
            self.cat_layout,
            [format_display_name(category) for category in self.categories],
            self._handle_category_button,
        )
        sync_exclusive_button_row(
            self.category_buttons,
            format_display_name(self.current_category) if self.current_category else None,
        )

    def _handle_category_button(self, label: str, checked: bool) -> None:
        category = resolve_category_name(self.categories, label)
        self.select_category(category, checked)

    def refresh_cart(self):
        self.cart_list.clear()
        for item in self.cart.items:
            self.cart_list.addItem(
                f"{item.product.name} x{item.quantity} = {CURRENCY}{item.total_price:.2f}"
            )
        self.total_label.setText(f"Total: {CURRENCY}{self.cart.total():.2f}")

    def format_transaction_text(self, transaction: Transaction) -> str:
        lines = [
            f"Receipt #{transaction.id or '-'}",
            f"Shift: #{transaction.shift_id or '-'}",
            f"Date: {transaction.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Payment: {transaction.payment_method}",
            "",
            "Items",
        ]
        if not transaction.items:
            lines.append("No items recorded.")
        for item in transaction.items:
            lines.append(
                f"{item.product_name} x{item.quantity} @ {CURRENCY}{item.unit_price:.2f} = {CURRENCY}{item.line_total:.2f}"
            )
        lines.extend(
            [
                "",
                f"Total: {CURRENCY}{transaction.total:.2f}",
            ]
        )
        return "\n".join(lines)

    def show_receipt_dialog(self, transaction: Transaction, title: str = "Receipt") -> None:
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(460, 520)

        layout = QtWidgets.QVBoxLayout(dialog)
        receipt = QtWidgets.QTextEdit()
        receipt.setReadOnly(True)
        receipt.setPlainText(self.format_transaction_text(transaction))
        layout.addWidget(receipt)

        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)

        dialog.exec()

    def choose_payment_method(self) -> str | None:
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Checkout")
        dialog.resize(420, 220)

        layout = QtWidgets.QVBoxLayout(dialog)
        layout.addWidget(QtWidgets.QLabel("Choose payment method:"))

        selected_method: dict[str, str | None] = {"value": None}

        def select_method(method: str) -> None:
            selected_method["value"] = method
            dialog.accept()

        button_layout = QtWidgets.QGridLayout()
        layout.addLayout(button_layout)
        for index, method in enumerate(CHECKOUT_PAYMENT_METHODS):
            button = QtWidgets.QPushButton(method)
            button.setMinimumHeight(56)
            button.clicked.connect(lambda _checked=False, payment_method=method: select_method(payment_method))
            button_layout.addWidget(button, index // 2, index % 2)

        cancel_button = QtWidgets.QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        layout.addWidget(cancel_button)

        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return None
        return selected_method["value"]

    def get_product_by_id(self, product_id: int | None) -> Product | None:
        if product_id is None:
            return None
        return next((product for product in self.inventory.list_products() if product.id == product_id), None)

    def edit_product(self, product: Product) -> bool:
        result = prompt_edit_product(self, product, self.categories, self.subcategory_map)
        if result is None:
            return False
        category = resolve_category_name(self.categories, result.category)
        sub_category = resolve_subcategory_name(self.subcategory_map, category, result.sub_category)
        product.name = result.name
        product.price = result.price
        product.category = category
        product.sub_category = sub_category
        product.color = self.get_preset_color(category, sub_category)
        self.inventory.update_product(product)
        self.refresh_products()
        return True

    def delete_product(self, product: Product) -> bool:
        reply = QtWidgets.QMessageBox.question(
            self,
            "Delete product",
            f"Are you sure you want to delete '{product.name}'?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return False
        self.inventory.delete_product(product.id)
        self.refresh_products()
        return True


    def add_product_dialog(self, require_pin: bool = True):
        if require_pin and not self.check_pin():
            return
        result = prompt_new_product(self, self.categories, self.subcategory_map)
        if result is None:
            return
        category = resolve_category_name(self.categories, result.category)
        sub_category = resolve_subcategory_name(self.subcategory_map, category, result.sub_category)
        color = self.get_preset_color(category, sub_category)
        self.inventory.add_product(
            result.name,
            result.price,
            category=category,
            sub_category=sub_category,
            color=color,
        )
        # do not automatically change filter; user will press category button to view
        self.refresh_products()

    def select_category(self, category: str, checked: bool):
        # toggle category filter and update subcategories
        if checked:
            self.current_category = resolve_category_name(self.categories, category)
            self.current_subcategory = None
            self.update_subcategories(self.current_category)
        else:
            self.current_category = None
            self.current_subcategory = None
            self.update_subcategories(None)
        sync_exclusive_button_row(
            self.category_buttons,
            format_display_name(self.current_category) if self.current_category else None,
        )
        self.refresh_products()

    def update_subcategories(self, category: str | None):
        category = resolve_category_name(self.categories, category)
        subcategories = get_subcategories_for_category(self.subcategory_map, category)
        if category and subcategories:
            self.subcategory_buttons = rebuild_toggle_button_row(
                self.subcat_layout,
                subcategories,
                self.select_subcategory,
            )
            self.subcat_widget.setVisible(True)
        else:
            self.subcategory_buttons = {}
            clear_layout_widgets(self.subcat_layout)
            self.subcat_widget.setVisible(False)
        sync_exclusive_button_row(self.subcategory_buttons, self.current_subcategory)

    def select_subcategory(self, sub: str, checked: bool):
        if checked:
            self.current_subcategory = resolve_subcategory_name(
                self.subcategory_map,
                self.current_category,
                sub,
            )
        else:
            self.current_subcategory = None
        sync_exclusive_button_row(self.subcategory_buttons, self.current_subcategory)
        self.refresh_products()

    def select_product(self, pid: int, checked: bool):
        if checked:
            self.selected_product_id = pid
        else:
            self.selected_product_id = None
        # update all button styles
        for id_, btn in self.product_buttons.items():
            self.apply_button_style(id_, selected=(id_ == self.selected_product_id))

    def apply_button_style(self, pid: int, selected: bool) -> None:
        btn = self.product_buttons.get(pid)
        if not btn:
            return
        font_size = btn.property("product_font_size") or 10
        base = f"text-align: center; font-size: {font_size}pt; color: white;"
        color = self.product_colors.get(pid, "")
        if color:
            base += f" background-color: {color};"
        if selected:
            base += " border: 4px solid #ffd400;"
        else:
            base += " border: 1px solid #3a3a3a;"
        btn.setStyleSheet(base)

    def get_preset_color(self, category: str, sub_category: str = "") -> str:
        return get_preset_color_value(
            self.category_color_presets,
            self.subcategory_color_presets,
            category,
            sub_category,
        )

    def edit_color_presets(self, require_pin: bool = True):
        if require_pin and not self.check_pin():
            return
        result = edit_color_presets_dialog(
            self,
            self.categories,
            self.subcategory_map,
            self.category_color_presets,
            self.subcategory_color_presets,
        )
        if result is None:
            return

        self.category_color_presets, self.subcategory_color_presets, apply_now = result
        save_color_presets(self.category_color_presets, self.subcategory_color_presets)

        if apply_now:
            self.apply_presets_to_existing_products()
        else:
            self.refresh_products()

    def apply_presets_to_existing_products(self):
        for product in self.inventory.list_products():
            product.color = self.get_preset_color(product.category, product.sub_category)
            self.inventory.update_product(product)
        self.refresh_products()

    def edit_categories(self, require_pin: bool = True):
        if require_pin and not self.check_pin():
            return

        result = edit_categories_dialog(
            self,
            self.categories,
            self.subcategory_map,
            self.category_color_presets,
            self.subcategory_color_presets,
            self.inventory.list_products(),
        )
        if result is None:
            return

        self.categories = result.categories
        self.subcategory_map = result.subcategory_map
        self.category_color_presets = result.category_color_presets
        self.subcategory_color_presets = result.subcategory_color_presets

        for product in self.inventory.list_products():
            final_category = result.category_renames.get(product.category, product.category)
            final_subcategory = result.subcategory_renames.get((final_category, product.sub_category), product.sub_category)
            product.category = final_category
            product.sub_category = final_subcategory
            product.color = self.get_preset_color(product.category, product.sub_category)
            self.inventory.update_product(product)

        if self.current_category and not any(names_match(self.current_category, category) for category in self.categories):
            self.current_category = None
            self.current_subcategory = None
        else:
            self.current_category = resolve_category_name(self.categories, self.current_category)

        if category_requires_subcategory(self.subcategory_map, self.current_category):
            valid_subcategories = get_subcategories_for_category(self.subcategory_map, self.current_category)
            if self.current_subcategory and not any(
                names_match(self.current_subcategory, subcategory)
                for subcategory in valid_subcategories
            ):
                self.current_subcategory = None
            else:
                self.current_subcategory = resolve_subcategory_name(
                    self.subcategory_map,
                    self.current_category,
                    self.current_subcategory,
                )
        else:
            self.current_subcategory = None

        save_category_config(self.categories, self.subcategory_map)
        save_color_presets(self.category_color_presets, self.subcategory_color_presets)
        self.rebuild_category_buttons()
        self.update_subcategories(self.current_category)
        self.refresh_products()

    def choose_product_from_inventory(self, title: str, prompt: str) -> Product | None:
        return choose_product_dialog(
            self,
            self.inventory.list_products(),
            title,
            prompt,
            currency_symbol=CURRENCY,
        )

    def check_pin(self) -> bool:
        """Ask the user for the PIN, return True if correct."""
        manager_pin = load_manager_pin()
        if not manager_pin:
            QtWidgets.QMessageBox.warning(
                self,
                "PIN",
                "No manager PIN is configured. Set TILL_MANAGER_PIN or create till/local_settings.json.",
            )
            return False
        return request_pin(self, manager_pin)

    def adjust_selected_product_font(self, require_pin: bool = True):
        if require_pin and not self.check_pin():
            return
        if self.selected_product_id is None:
            QtWidgets.QMessageBox.information(self, "Adjust product font", "Select a product first.")
            return
        product = next((p for p in self.inventory.list_products() if p.id == self.selected_product_id), None)
        if not product:
            return
        font_size, ok = QtWidgets.QInputDialog.getInt(
            self,
            "Adjust product font",
            "Font size:",
            value=product.font_size or 10,
            min=8,
            max=24,
            step=1,
        )
        if not ok:
            return
        product.font_size = font_size
        self.inventory.update_product(product)
        self.refresh_products()
        if names_match(self.current_category, product.category) and names_match(
            self.current_subcategory,
            product.sub_category,
        ):
            button = self.product_buttons.get(product.id)
            if button:
                button.setChecked(True)
            self.selected_product_id = product.id
            self.apply_button_style(product.id, selected=True)

    def edit_grid_layout(self, require_pin: bool = True):
        if require_pin and not self.check_pin():
            return

        layout_choice = choose_grid_layout_dialog(
            self,
            GRID_LAYOUT_PRESETS,
            (self.grid_columns, self.grid_rows),
        )
        if layout_choice is None:
            return

        self.grid_columns, self.grid_rows = layout_choice
        save_grid_layout(self.grid_columns, self.grid_rows)
        self.apply_grid_layout_settings()
        self.refresh_products()

    def add_selected_to_cart(self):
        if self.selected_product_id is None:
            return
        prod = next((p for p in self.inventory.list_products() if p.id == self.selected_product_id), None)
        if prod:
            self.cart.add_item(prod)
            self.refresh_cart()

    def delete_selected_product(self, require_pin: bool = True):
        if require_pin and not self.check_pin():
            return
        product = self.choose_product_from_inventory(
            "Delete product",
            "Find a product to delete:",
        )
        if not product:
            return
        self.delete_product(product)

    def edit_selected_product(self, require_pin: bool = True):
        if require_pin and not self.check_pin():
            return
        # choose from all products so manager can search/edit any item
        prod = self.choose_product_from_inventory(
            "Edit product",
            "Find a product to edit:",
        )
        if not prod:
            return
        self.edit_product(prod)

    def open_manager_dialog(self):
        if not self.check_pin():
            return

        show_manager_dialog(
            self,
            product_actions={
                "Add Product": lambda: self.add_product_dialog(require_pin=False),
                "Edit Categories": lambda: self.edit_categories(require_pin=False),
                "Edit Product": lambda: self.edit_selected_product(require_pin=False),
                "Delete Product": lambda: self.delete_selected_product(require_pin=False),
            },
            design_actions={
                "Color Presets": lambda: self.edit_color_presets(require_pin=False),
                "Adjust Product Font": lambda: self.adjust_selected_product_font(require_pin=False),
                "Grid Layout": lambda: self.edit_grid_layout(require_pin=False),
                "Rearrange Grid Items": lambda: self.rearrange_grid_items(require_pin=False),
            },
        )

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        closed_db_ids: set[int] = set()
        for db in (
            getattr(self.inventory, "db", None),
            getattr(self.cart, "db", None),
        ):
            if db is None or id(db) in closed_db_ids:
                continue
            try:
                db.close()
            except Exception:
                pass
            closed_db_ids.add(id(db))
        close_db()
        super().closeEvent(event)

    def rearrange_grid_items(self, require_pin: bool = True):
        if require_pin and not self.check_pin():
            return
        if not self.current_category:
            QtWidgets.QMessageBox.information(self, "Rearrange Grid Items", "Select a category first.")
            return
        if category_requires_subcategory(self.subcategory_map, self.current_category) and not self.current_subcategory:
            QtWidgets.QMessageBox.information(self, "Rearrange Grid Items", "Select a subcategory first.")
            return

        working_products = list(self.get_visible_products())
        if not working_products:
            QtWidgets.QMessageBox.information(self, "Rearrange Grid Items", "No products available in the current view.")
            return

        positions = show_grid_reorder_dialog(
            self,
            working_products,
            self.current_category,
            self.current_subcategory,
            self.grid_columns,
            self.grid_rows,
        )
        if positions is None:
            return

        for index, (product, row, column) in enumerate(positions, start=1):
            product.tile_order = index
            product.tile_row = row
            product.tile_column = column
            self.inventory.update_product(product)
        self.refresh_products()

    def remove_selected_from_cart(self):
        if not self.check_pin():
            return
        row = self.cart_list.currentRow()
        if row < 0:
            return
        del self.cart.items[row]
        self.refresh_cart()

    def perform_checkout(self):
        total = self.cart.total()
        if total == 0:
            QtWidgets.QMessageBox.warning(self, "Checkout", "Cart is empty")
            return
        payment_method = self.choose_payment_method()
        if payment_method is None:
            return
        txn = self.cart.checkout(payment_method=payment_method)
        backup_error = self.create_automatic_backup()
        self.refresh_cart()
        self.refresh_bills()
        self.show_receipt_dialog(txn, title="Receipt")
        if backup_error is not None:
            QtWidgets.QMessageBox.warning(
                self,
                "Backup Data",
                f"Automatic checkout backup failed.\n\n{backup_error}",
            )
