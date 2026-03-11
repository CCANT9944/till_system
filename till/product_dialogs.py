"""Product add/edit dialog helpers for the till UI."""

from __future__ import annotations

from dataclasses import dataclass

from PyQt6 import QtWidgets

from .categories import get_subcategories_for_category, resolve_category_name, resolve_subcategory_name
from .models import Product


@dataclass
class ProductDialogResult:
    name: str
    price: float
    category: str
    sub_category: str


def _choose_subcategory(
    parent: QtWidgets.QWidget,
    category: str,
    subcategory_map: dict[str, list[str]],
    current_subcategory: str = "",
) -> str | None:
    options = get_subcategories_for_category(subcategory_map, category)
    if not options:
        return ""

    current_subcategory = resolve_subcategory_name(subcategory_map, category, current_subcategory)
    current_index = options.index(current_subcategory) if current_subcategory in options else 0
    sub_cat, ok = QtWidgets.QInputDialog.getItem(
        parent,
        "Subcategory",
        "Select type:",
        options,
        editable=True,
        current=current_index,
    )
    if not ok:
        return None
    return sub_cat


def prompt_new_product(
    parent: QtWidgets.QWidget,
    categories: list[str],
    subcategory_map: dict[str, list[str]],
) -> ProductDialogResult | None:
    name, ok = QtWidgets.QInputDialog.getText(parent, "New Product", "Name:")
    if not ok or not name:
        return None

    price, ok2 = QtWidgets.QInputDialog.getDouble(
        parent,
        "New Product",
        "Price:",
        decimals=2,
        min=0.0,
        max=10_000_000.0,
    )
    if not ok2:
        return None

    category, ok3 = QtWidgets.QInputDialog.getItem(
        parent,
        "Category",
        "Select category:",
        categories,
        editable=True,
    )
    if not ok3:
        return None

    category = resolve_category_name(categories, category)

    sub_cat = _choose_subcategory(parent, category, subcategory_map)
    if sub_cat is None:
        return None

    sub_cat = resolve_subcategory_name(subcategory_map, category, sub_cat)

    return ProductDialogResult(name=name, price=price, category=category, sub_category=sub_cat)


def prompt_edit_product(
    parent: QtWidgets.QWidget,
    product: Product,
    categories: list[str],
    subcategory_map: dict[str, list[str]],
) -> ProductDialogResult | None:
    name, ok = QtWidgets.QInputDialog.getText(parent, "Edit Product", "Name:", text=product.name)
    if not ok or not name:
        return None

    price, ok2 = QtWidgets.QInputDialog.getDouble(
        parent,
        "Edit Product",
        "Price:",
        value=product.price,
        decimals=2,
        min=0.0,
        max=10_000_000.0,
    )
    if not ok2:
        return None

    category, ok3 = QtWidgets.QInputDialog.getItem(
        parent,
        "Category",
        "Select category:",
        categories,
        editable=True,
        current=categories.index(product.category) if product.category in categories else 0,
    )
    if not ok3:
        return None

    category = resolve_category_name(categories, category)

    sub_cat = _choose_subcategory(parent, category, subcategory_map, product.sub_category)
    if sub_cat is None:
        return None

    sub_cat = resolve_subcategory_name(subcategory_map, category, sub_cat)

    return ProductDialogResult(name=name, price=price, category=category, sub_category=sub_cat)