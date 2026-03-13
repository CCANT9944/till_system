import importlib
import types

import pytest

from interface.till.grid_layout import GRID_LAYOUT_PRESETS
from interface.till.models import Product


QtWidgets = None
TEST_PIN = "2468"
if importlib.util.find_spec("PyQt6") is not None:
    dialog_helpers = importlib.import_module("interface.till.dialog_helpers")
    grid_reorder_dialog = importlib.import_module("interface.till.grid_reorder_dialog")
    product_dialogs = importlib.import_module("interface.till.product_dialogs")
    QtWidgets = importlib.import_module("PyQt6.QtWidgets")
    choose_grid_layout_dialog = dialog_helpers.choose_grid_layout_dialog
    choose_product_dialog = dialog_helpers.choose_product_dialog
    request_pin = dialog_helpers.request_pin
    show_grid_reorder_dialog = grid_reorder_dialog.show_grid_reorder_dialog
    prompt_edit_product = product_dialogs.prompt_edit_product
    prompt_new_product = product_dialogs.prompt_new_product


def ensure_qt():
    if QtWidgets is None:
        pytest.skip("PyQt6 not available")


def test_choose_product_dialog_returns_none_when_inventory_empty(monkeypatch):
    ensure_qt()
    called = {}

    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "information",
        staticmethod(lambda _parent, title, message: called.update({"title": title, "message": message})),
    )

    result = choose_product_dialog(None, [], "Pick product", "Choose one")

    assert result is None
    assert called == {"title": "Pick product", "message": "No products available."}


def test_request_pin_returns_true_for_matching_pin(monkeypatch):
    ensure_qt()

    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getText",
        staticmethod(lambda *args, **kwargs: (TEST_PIN, True)),
    )

    assert request_pin(None, TEST_PIN) is True


def test_request_pin_warns_on_incorrect_pin(monkeypatch):
    ensure_qt()
    called = {}

    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getText",
        staticmethod(lambda *args, **kwargs: ("9999", True)),
    )
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "warning",
        staticmethod(lambda _parent, title, message: called.update({"title": title, "message": message})),
    )

    assert request_pin(None, TEST_PIN) is False
    assert called == {"title": "PIN", "message": "Incorrect PIN"}


def test_choose_grid_layout_dialog_returns_selected_preset(monkeypatch):
    ensure_qt()

    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getItem",
        staticmethod(lambda *args, **kwargs: ("5 x 6", True)),
    )

    result = choose_grid_layout_dialog(None, GRID_LAYOUT_PRESETS, (6, 6))

    assert result == (5, 6)


def test_prompt_new_product_collects_subcategory(monkeypatch):
    ensure_qt()
    item_results = iter([("beer", True), ("Draught", True)])

    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getText",
        staticmethod(lambda *args, **kwargs: ("Lager", True)),
    )
    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getDouble",
        staticmethod(lambda *args, **kwargs: (3.5, True)),
    )
    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getItem",
        staticmethod(lambda *args, **kwargs: next(item_results)),
    )

    result = prompt_new_product(None, ["beer", "snacks"], {"beer": ["Draught", "Bottled"]})

    assert result is not None
    assert result.name == "Lager"
    assert result.price == pytest.approx(3.5)
    assert result.category == "beer"
    assert result.sub_category == "Draught"


def test_prompt_new_product_allows_blank_category(monkeypatch):
    ensure_qt()
    get_item_calls = []

    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getText",
        staticmethod(lambda *args, **kwargs: ("Water", True)),
    )
    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getDouble",
        staticmethod(lambda *args, **kwargs: (1.25, True)),
    )

    def fake_get_item(*args, **kwargs):
        get_item_calls.append((args, kwargs))
        return ("Uncategorised", True)

    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getItem",
        staticmethod(fake_get_item),
    )

    result = prompt_new_product(
        None,
        ["beer", "snacks"],
        {"beer": ["Draught", "Bottled"]},
        allow_empty_category=True,
    )

    assert result is not None
    assert result.name == "Water"
    assert result.price == pytest.approx(1.25)
    assert result.category == ""
    assert result.sub_category == ""
    assert len(get_item_calls) == 1
    assert get_item_calls[0][0][3][0] == "Uncategorised"


def test_prompt_edit_product_returns_empty_subcategory_for_plain_category(monkeypatch):
    ensure_qt()
    product = Product(name="Chips", price=1.2, category="snacks")

    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getText",
        staticmethod(lambda *args, **kwargs: ("Salted Chips", True)),
    )
    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getDouble",
        staticmethod(lambda *args, **kwargs: (1.4, True)),
    )
    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getItem",
        staticmethod(lambda *args, **kwargs: ("snacks", True)),
    )

    result = prompt_edit_product(None, product, ["beer", "snacks"], {"beer": ["Draught", "Bottled"]})

    assert result is not None
    assert result.name == "Salted Chips"
    assert result.price == pytest.approx(1.4)
    assert result.category == "snacks"
    assert result.sub_category == ""


def test_prompt_edit_product_allows_blank_category(monkeypatch):
    ensure_qt()
    product = Product(name="Tea", price=1.2, category="hot drinks")
    get_item_calls = []

    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getText",
        staticmethod(lambda *args, **kwargs: ("Tea", True)),
    )
    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getDouble",
        staticmethod(lambda *args, **kwargs: (1.2, True)),
    )
    def fake_get_item(*args, **kwargs):
        get_item_calls.append((args, kwargs))
        return ("Uncategorised", True)

    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getItem",
        staticmethod(fake_get_item),
    )

    result = prompt_edit_product(
        None,
        product,
        ["beer", "hot drinks", "snacks"],
        {"beer": ["Draught", "Bottled"]},
        allow_empty_category=True,
    )

    assert result is not None
    assert result.name == "Tea"
    assert result.price == pytest.approx(1.2)
    assert result.category == ""
    assert result.sub_category == ""
    assert get_item_calls[0][0][3][0] == "Uncategorised"


def test_show_grid_reorder_dialog_returns_board_positions(monkeypatch):
    ensure_qt()
    products = [Product(id=1, name="Tea", price=1.5)]
    expected_positions = [(products[0], 1, 2)]

    class FakeSignal:
        def connect(self, _callback):
            return None

    class FakeDialog:
        class DialogCode:
            Accepted = 1

        def __init__(self, _parent=None):
            pass

        def setWindowTitle(self, _title):
            return None

        def resize(self, _width, _height):
            return None

        def accept(self):
            return None

        def reject(self):
            return None

        def exec(self):
            return self.DialogCode.Accepted

    class FakeLayout:
        def __init__(self, *_args, **_kwargs):
            pass

        def addWidget(self, _widget):
            return None

        def addLayout(self, _layout):
            return None

    class FakeScrollArea:
        def setWidgetResizable(self, _value):
            return None

        def setWidget(self, _widget):
            return None

    class FakePushButton:
        def __init__(self, _label):
            self.clicked = FakeSignal()

    class FakeLabel:
        def __init__(self, _text):
            pass

    class FakeBoard:
        def __init__(self, _products, _columns, _rows, _parent):
            self._positions = expected_positions

        def get_positions(self):
            return self._positions

    fake_qtwidgets = types.SimpleNamespace(
        QDialog=FakeDialog,
        QVBoxLayout=FakeLayout,
        QHBoxLayout=FakeLayout,
        QLabel=FakeLabel,
        QScrollArea=FakeScrollArea,
        QPushButton=FakePushButton,
    )

    monkeypatch.setattr(grid_reorder_dialog, "QtWidgets", fake_qtwidgets)
    monkeypatch.setattr(grid_reorder_dialog, "GridReorderBoard", FakeBoard)

    result = show_grid_reorder_dialog(None, products, "hot drinks", None, 6, 6)

    assert result == expected_positions