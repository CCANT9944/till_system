"""Category editor dialog for the till UI."""

from __future__ import annotations

from dataclasses import dataclass

from PyQt6 import QtWidgets

from .categories import names_match
from .models import Product


@dataclass
class CategoryEditorResult:
    categories: list[str]
    subcategory_map: dict[str, list[str]]
    category_color_presets: dict[str, str]
    subcategory_color_presets: dict[tuple[str, str], str]
    category_renames: dict[str, str]
    subcategory_renames: dict[tuple[str, str], str]


def edit_categories_dialog(
    parent: QtWidgets.QWidget,
    categories: list[str],
    subcategory_map: dict[str, list[str]],
    category_color_presets: dict[str, str],
    subcategory_color_presets: dict[tuple[str, str], str],
    products: list[Product],
) -> CategoryEditorResult | None:
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle("Edit Categories")
    dialog.resize(760, 460)

    layout = QtWidgets.QVBoxLayout(dialog)
    info = QtWidgets.QLabel("Add, reorder, rename, or remove categories and their subcategories.")
    layout.addWidget(info)

    content_layout = QtWidgets.QHBoxLayout()
    layout.addLayout(content_layout)

    left_panel = QtWidgets.QWidget()
    left_layout = QtWidgets.QVBoxLayout(left_panel)
    left_layout.addWidget(QtWidgets.QLabel("Categories"))
    category_list = QtWidgets.QListWidget()
    left_layout.addWidget(category_list)

    category_button_row = QtWidgets.QHBoxLayout()
    left_layout.addLayout(category_button_row)
    add_button = QtWidgets.QPushButton("Add")
    rename_button = QtWidgets.QPushButton("Rename")
    delete_button = QtWidgets.QPushButton("Delete")
    category_button_row.addWidget(add_button)
    category_button_row.addWidget(rename_button)
    category_button_row.addWidget(delete_button)

    reorder_row = QtWidgets.QHBoxLayout()
    left_layout.addLayout(reorder_row)
    up_button = QtWidgets.QPushButton("Move Up")
    down_button = QtWidgets.QPushButton("Move Down")
    reorder_row.addWidget(up_button)
    reorder_row.addWidget(down_button)

    right_panel = QtWidgets.QWidget()
    right_layout = QtWidgets.QVBoxLayout(right_panel)
    selected_category_label = QtWidgets.QLabel("Subcategories")
    right_layout.addWidget(selected_category_label)
    subcategory_list = QtWidgets.QListWidget()
    right_layout.addWidget(subcategory_list)

    subcategory_button_row = QtWidgets.QHBoxLayout()
    right_layout.addLayout(subcategory_button_row)
    add_subcategory_button = QtWidgets.QPushButton("Add")
    rename_subcategory_button = QtWidgets.QPushButton("Rename")
    delete_subcategory_button = QtWidgets.QPushButton("Delete")
    subcategory_button_row.addWidget(add_subcategory_button)
    subcategory_button_row.addWidget(rename_subcategory_button)
    subcategory_button_row.addWidget(delete_subcategory_button)

    content_layout.addWidget(left_panel, 1)
    content_layout.addWidget(right_panel, 1)

    close_row = QtWidgets.QHBoxLayout()
    layout.addLayout(close_row)
    save_button = QtWidgets.QPushButton("Save")
    cancel_button = QtWidgets.QPushButton("Cancel")
    close_row.addWidget(save_button)
    close_row.addWidget(cancel_button)

    working_categories = list(categories)
    working_subcategory_map = {category: list(values) for category, values in subcategory_map.items()}
    working_category_color_presets = dict(category_color_presets)
    working_subcategory_color_presets = dict(subcategory_color_presets)
    category_renames: dict[str, str] = {}
    subcategory_renames: dict[tuple[str, str], str] = {}

    def get_selected_category() -> str | None:
        item = category_list.currentItem()
        return item.text() if item else None

    def current_product_usage(category_name: str, subcategory_name: str | None = None) -> bool:
        for product in products:
            effective_category = category_renames.get(product.category, product.category)
            effective_subcategory = subcategory_renames.get(
                (effective_category, product.sub_category),
                product.sub_category,
            )
            if not names_match(effective_category, category_name):
                continue
            if subcategory_name is None:
                return True
            if names_match(effective_subcategory, subcategory_name):
                return True
        return False

    def refresh_subcategory_list(select_name: str | None = None):
        selected_category = get_selected_category()
        selected_category_label.setText(
            f"Subcategories for {selected_category}" if selected_category else "Subcategories"
        )
        subcategory_list.clear()
        if not selected_category:
            return
        for value in working_subcategory_map.get(selected_category, []):
            subcategory_list.addItem(value)
        if subcategory_list.count() == 0:
            return
        target_name = select_name or subcategory_list.item(0).text()
        for index in range(subcategory_list.count()):
            if subcategory_list.item(index).text() == target_name:
                subcategory_list.setCurrentRow(index)
                break

    def refresh_category_list(select_name: str | None = None):
        category_list.clear()
        category_list.addItems(working_categories)
        if category_list.count() == 0:
            refresh_subcategory_list()
            return
        target_name = select_name or category_list.item(0).text()
        for index in range(category_list.count()):
            if category_list.item(index).text() == target_name:
                category_list.setCurrentRow(index)
                break
        refresh_subcategory_list()

    def add_category():
        name, ok = QtWidgets.QInputDialog.getText(dialog, "Add Category", "Category name:")
        if not ok or not name.strip():
            return
        normalized = name.strip()
        if normalized.lower() in {category.lower() for category in working_categories}:
            QtWidgets.QMessageBox.warning(dialog, "Add Category", "Category already exists.")
            return
        working_categories.append(normalized)
        refresh_category_list(normalized)

    def rename_category():
        old_name = get_selected_category()
        if old_name is None:
            return
        new_name, ok = QtWidgets.QInputDialog.getText(dialog, "Rename Category", "New category name:", text=old_name)
        if not ok or not new_name.strip():
            return
        new_name = new_name.strip()
        if new_name.lower() != old_name.lower() and new_name.lower() in {category.lower() for category in working_categories}:
            QtWidgets.QMessageBox.warning(dialog, "Rename Category", "Category already exists.")
            return
        index = working_categories.index(old_name)
        working_categories[index] = new_name
        category_renames[old_name] = new_name

        if old_name in working_subcategory_map:
            working_subcategory_map[new_name] = working_subcategory_map.pop(old_name)
        if old_name in working_category_color_presets:
            working_category_color_presets[new_name] = working_category_color_presets.pop(old_name)

        sub_updates = {}
        for (category_name, subcategory), _color in list(working_subcategory_color_presets.items()):
            if category_name == old_name:
                sub_updates[(new_name, subcategory)] = working_subcategory_color_presets.pop((category_name, subcategory))
        working_subcategory_color_presets.update(sub_updates)

        renamed_subcategories = {}
        for (category_name, subcategory), renamed_value in list(subcategory_renames.items()):
            if category_name == old_name:
                renamed_subcategories[(new_name, subcategory)] = subcategory_renames.pop((category_name, subcategory))
        subcategory_renames.update(renamed_subcategories)

        refresh_category_list(new_name)

    def delete_category():
        category_name = get_selected_category()
        if category_name is None:
            return
        if len(working_categories) == 1:
            QtWidgets.QMessageBox.warning(dialog, "Delete Category", "At least one category must remain.")
            return
        if current_product_usage(category_name):
            QtWidgets.QMessageBox.warning(
                dialog,
                "Delete Category",
                "This category is still used by existing products. Move or delete those products first.",
            )
            return
        working_categories.remove(category_name)
        working_subcategory_map.pop(category_name, None)
        working_category_color_presets.pop(category_name, None)
        for key in list(working_subcategory_color_presets):
            if key[0] == category_name:
                working_subcategory_color_presets.pop(key)
        for key in list(subcategory_renames):
            if key[0] == category_name:
                subcategory_renames.pop(key)
        next_name = working_categories[0] if working_categories else None
        refresh_category_list(next_name)

    def move_category(direction: int):
        category_name = get_selected_category()
        if category_name is None:
            return
        index = working_categories.index(category_name)
        new_index = index + direction
        if new_index < 0 or new_index >= len(working_categories):
            return
        working_categories[index], working_categories[new_index] = working_categories[new_index], working_categories[index]
        refresh_category_list(category_name)

    def add_subcategory():
        category_name = get_selected_category()
        if category_name is None:
            return
        name, ok = QtWidgets.QInputDialog.getText(dialog, "Add Subcategory", "Subcategory name:")
        if not ok or not name.strip():
            return
        normalized = name.strip()
        existing = working_subcategory_map.setdefault(category_name, [])
        if normalized.lower() in {subcategory.lower() for subcategory in existing}:
            QtWidgets.QMessageBox.warning(dialog, "Add Subcategory", "Subcategory already exists.")
            return
        existing.append(normalized)
        refresh_subcategory_list(normalized)

    def rename_subcategory():
        category_name = get_selected_category()
        item = subcategory_list.currentItem()
        if category_name is None or item is None:
            return
        old_name = item.text()
        new_name, ok = QtWidgets.QInputDialog.getText(dialog, "Rename Subcategory", "New subcategory name:", text=old_name)
        if not ok or not new_name.strip():
            return
        new_name = new_name.strip()
        existing = working_subcategory_map.get(category_name, [])
        if new_name.lower() != old_name.lower() and new_name.lower() in {subcategory.lower() for subcategory in existing}:
            QtWidgets.QMessageBox.warning(dialog, "Rename Subcategory", "Subcategory already exists.")
            return
        index = existing.index(old_name)
        existing[index] = new_name
        subcategory_renames[(category_name, old_name)] = new_name
        if (category_name, old_name) in working_subcategory_color_presets:
            working_subcategory_color_presets[(category_name, new_name)] = working_subcategory_color_presets.pop((category_name, old_name))
        refresh_subcategory_list(new_name)

    def delete_subcategory():
        category_name = get_selected_category()
        item = subcategory_list.currentItem()
        if category_name is None or item is None:
            return
        subcategory_name = item.text()
        if current_product_usage(category_name, subcategory_name):
            QtWidgets.QMessageBox.warning(
                dialog,
                "Delete Subcategory",
                "This subcategory is still used by existing products. Move or edit those products first.",
            )
            return
        existing = working_subcategory_map.get(category_name, [])
        if subcategory_name in existing:
            existing.remove(subcategory_name)
        working_subcategory_color_presets.pop((category_name, subcategory_name), None)
        subcategory_renames.pop((category_name, subcategory_name), None)
        if not existing:
            working_subcategory_map.pop(category_name, None)
        refresh_subcategory_list()

    add_button.clicked.connect(add_category)
    rename_button.clicked.connect(rename_category)
    delete_button.clicked.connect(delete_category)
    up_button.clicked.connect(lambda: move_category(-1))
    down_button.clicked.connect(lambda: move_category(1))
    add_subcategory_button.clicked.connect(add_subcategory)
    rename_subcategory_button.clicked.connect(rename_subcategory)
    delete_subcategory_button.clicked.connect(delete_subcategory)
    category_list.itemSelectionChanged.connect(refresh_subcategory_list)
    save_button.clicked.connect(dialog.accept)
    cancel_button.clicked.connect(dialog.reject)

    refresh_category_list()

    if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return None

    return CategoryEditorResult(
        categories=working_categories,
        subcategory_map=working_subcategory_map,
        category_color_presets=working_category_color_presets,
        subcategory_color_presets=working_subcategory_color_presets,
        category_renames=category_renames,
        subcategory_renames=subcategory_renames,
    )