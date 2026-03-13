import datetime
import importlib

import pytest

QtWidgets = None
if importlib.util.find_spec("PyQt6") is not None:
    QtWidgets = importlib.import_module("PyQt6.QtWidgets")

from interface.till.bill_dialogs import prompt_edit_bill
from interface.till.controller import InventoryController
from interface.till.db import Database
from interface.till.models import Product, Transaction, TransactionItem


class _ParentWithInventory(QtWidgets.QWidget if QtWidgets is not None else object):
    def __init__(self, inventory):
        if QtWidgets is not None:
            super().__init__()
        self.inventory = inventory


def test_prompt_edit_bill_can_add_item_by_search(tmp_path, monkeypatch):
    if QtWidgets is None:
        pytest.skip("PyQt6 not available")

    db = Database(path=tmp_path / "edit_bill_search.db")
    inv = InventoryController(db=db)
    coffee = inv.add_product("Coffee", 2.50, category="Hot Drinks")
    cake = inv.add_product("Cake", 4.00, category="Snacks")
    parent = _ParentWithInventory(inv)
    transaction = Transaction(
        id=7,
        payment_method="Cash",
        timestamp=datetime.datetime(2026, 3, 12, 10, 0, 0),
        items=[
            TransactionItem(
                product_id=coffee.id,
                product_name="Coffee",
                unit_price=2.50,
                quantity=1,
                category="Hot Drinks",
                sub_category="",
            )
        ],
    )

    import interface.till.bill_dialogs as bill_dialogs

    monkeypatch.setattr(bill_dialogs, "choose_product_dialog", lambda *args, **kwargs: cake)

    original_exec = QtWidgets.QDialog.exec

    def fake_exec(self):
        buttons = self.findChildren(QtWidgets.QPushButton)
        add_item = next(button for button in buttons if button.text() == "Add Item")
        save = next(button for button in buttons if button.text() in {"Save", "&Save"})
        table = self.findChild(QtWidgets.QTableWidget)
        assert table is not None
        add_item.click()
        assert table.currentRow() == 1
        assert table.item(1, 0).text() == "Cake"
        assert table.item(1, 4).text() == "Added"
        save.click()
        return QtWidgets.QDialog.DialogCode.Accepted

    monkeypatch.setattr(QtWidgets.QDialog, "exec", fake_exec)
    try:
        result = prompt_edit_bill(parent, transaction)
    finally:
        monkeypatch.setattr(QtWidgets.QDialog, "exec", original_exec)

    assert result is not None
    assert [item.product_name for item in result.items] == ["Coffee", "Cake"]
    assert result.items[1].product_id == cake.id
    assert result.items[1].unit_price == pytest.approx(4.0)
    assert result.items[1].quantity == 1
    assert result.items[1].category == "Snacks"
    assert result.total == pytest.approx(6.5)


def test_prompt_edit_bill_highlights_changed_and_removed_items(tmp_path, monkeypatch):
    if QtWidgets is None:
        pytest.skip("PyQt6 not available")

    db = Database(path=tmp_path / "edit_bill_changes.db")
    inv = InventoryController(db=db)
    coffee = inv.add_product("Coffee", 2.50, category="Hot Drinks")
    cake = inv.add_product("Cake", 4.00, category="Snacks")
    parent = _ParentWithInventory(inv)
    transaction = Transaction(
        id=8,
        payment_method="Cash",
        timestamp=datetime.datetime(2026, 3, 12, 11, 0, 0),
        items=[
            TransactionItem(
                product_id=coffee.id,
                product_name="Coffee",
                unit_price=2.50,
                quantity=1,
                category="Hot Drinks",
                sub_category="",
            ),
            TransactionItem(
                product_id=cake.id,
                product_name="Cake",
                unit_price=4.00,
                quantity=1,
                category="Snacks",
                sub_category="",
            ),
        ],
    )

    original_exec = QtWidgets.QDialog.exec

    def fake_exec(self):
        table = self.findChild(QtWidgets.QTableWidget)
        removed_items_list = self.findChild(QtWidgets.QListWidget, "removedItemsList")
        remove_button = next(
            button for button in self.findChildren(QtWidgets.QPushButton) if button.text() == "Remove Selected"
        )
        save = next(button for button in self.findChildren(QtWidgets.QPushButton) if button.text() in {"Save", "&Save"})

        assert table is not None
        assert removed_items_list is not None
        table.item(0, 1).setText("3")
        assert table.item(0, 4).text() == "Qty"
        table.selectRow(1)
        remove_button.click()
        assert removed_items_list.count() == 1
        assert "Cake x1 @ £4.00 = £4.00" == removed_items_list.item(0).text()
        save.click()
        return QtWidgets.QDialog.DialogCode.Accepted

    monkeypatch.setattr(QtWidgets.QDialog, "exec", fake_exec)
    try:
        result = prompt_edit_bill(parent, transaction)
    finally:
        monkeypatch.setattr(QtWidgets.QDialog, "exec", original_exec)

    assert result is not None
    assert len(result.items) == 1
    assert result.items[0].product_name == "Coffee"
    assert result.items[0].quantity == 3
    assert result.total == pytest.approx(7.5)