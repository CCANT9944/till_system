"""Reusable dialog helpers for the till UI."""

from __future__ import annotations

from PyQt6 import QtCore, QtWidgets

from .models import Product


def choose_product_dialog(
    parent: QtWidgets.QWidget,
    products: list[Product],
    title: str,
    prompt: str,
    currency_symbol: str = "£",
) -> Product | None:
    if not products:
        QtWidgets.QMessageBox.information(parent, title, "No products available.")
        return None

    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.resize(520, 420)

    layout = QtWidgets.QVBoxLayout(dialog)
    label = QtWidgets.QLabel(prompt)
    layout.addWidget(label)

    search_box = QtWidgets.QLineEdit()
    search_box.setPlaceholderText("Search by name, category, or subcategory")
    layout.addWidget(search_box)

    product_list = QtWidgets.QListWidget()
    layout.addWidget(product_list)

    button_box = QtWidgets.QDialogButtonBox(
        QtWidgets.QDialogButtonBox.StandardButton.Ok
        | QtWidgets.QDialogButtonBox.StandardButton.Cancel
    )
    ok_button = button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
    ok_button.setEnabled(False)
    layout.addWidget(button_box)

    def build_label(product: Product) -> str:
        parts = [product.name, product.category]
        if product.sub_category:
            parts.append(product.sub_category)
        return f"{' | '.join(parts)} | {currency_symbol}{product.price:.2f}"

    def refill_list(query: str = "") -> None:
        product_list.clear()
        query_text = query.strip().lower()
        for product in products:
            haystack = " ".join([product.name, product.category, product.sub_category or ""]).lower()
            if query_text and query_text not in haystack:
                continue
            item = QtWidgets.QListWidgetItem(build_label(product))
            item.setData(QtCore.Qt.ItemDataRole.UserRole, product.id)
            product_list.addItem(item)
        if product_list.count() > 0:
            product_list.setCurrentRow(0)
            ok_button.setEnabled(True)
        else:
            ok_button.setEnabled(False)

    search_box.textChanged.connect(refill_list)
    product_list.itemSelectionChanged.connect(
        lambda: ok_button.setEnabled(product_list.currentItem() is not None)
    )
    product_list.itemDoubleClicked.connect(lambda _item: dialog.accept())
    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)

    refill_list()

    if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return None

    current_item = product_list.currentItem()
    if current_item is None:
        return None
    product_id = current_item.data(QtCore.Qt.ItemDataRole.UserRole)
    return next((product for product in products if product.id == product_id), None)


def request_pin(
    parent: QtWidgets.QWidget,
    expected_pin: str,
    title: str = "PIN Required",
    prompt: str = "Enter PIN:",
) -> bool:
    pin, ok = QtWidgets.QInputDialog.getText(
        parent,
        title,
        prompt,
        QtWidgets.QLineEdit.EchoMode.Password,
    )
    if not ok:
        return False
    if pin == expected_pin:
        return True
    QtWidgets.QMessageBox.warning(parent, "PIN", "Incorrect PIN")
    return False


def choose_grid_layout_dialog(
    parent: QtWidgets.QWidget,
    presets: dict[str, tuple[int, int]],
    current_layout: tuple[int, int],
) -> tuple[int, int] | None:
    options = list(presets.keys())
    current_index = 0
    for index, label in enumerate(options):
        if presets[label] == current_layout:
            current_index = index
            break

    choice, ok = QtWidgets.QInputDialog.getItem(
        parent,
        "Grid Layout",
        "Choose the till grid layout:",
        options,
        current=current_index,
        editable=False,
    )
    if not ok:
        return None
    return presets[choice]