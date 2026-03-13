import tempfile
import os
import importlib
import datetime
import sqlite3
from pathlib import Path

import pytest

QtWidgets = None
QtCore = None
if importlib.util.find_spec("PyQt6") is not None:
    QtWidgets = importlib.import_module("PyQt6.QtWidgets")
    QtCore = importlib.import_module("PyQt6.QtCore")

from interface.till.controller import InventoryController, CartController
from interface.till.categories import DEFAULT_CATEGORIES, DEFAULT_SUBCATEGORY_MAP
from interface.till.db import Database
from interface.till.grid_widgets import PRODUCT_TILE_SIZE
from interface.till.models import Product, Transaction, TransactionItem


@pytest.fixture(autouse=True)
def default_main_window_category_config(monkeypatch):
    import interface.till.views as views

    monkeypatch.setattr(
        views,
        "load_category_config",
        lambda: (
            list(DEFAULT_CATEGORIES),
            {key: list(values) for key, values in DEFAULT_SUBCATEGORY_MAP.items()},
        ),
    )


def _layout_texts(layout):
    texts = []
    for index in range(layout.count()):
        widget = layout.itemAt(index).widget()
        if widget is not None and hasattr(widget, "text"):
            texts.append(widget.text().lower())
    return texts


def _expected_board_width(win):
    horizontal_spacing = max(win.product_layout.horizontalSpacing(), 0)
    return (win.grid_columns * PRODUCT_TILE_SIZE) + ((win.grid_columns - 1) * horizontal_spacing) + 4


def _table_rows(table):
    rows = []
    for row in range(table.rowCount()):
        rows.append(
            [
                table.item(row, column).text() if table.item(row, column) is not None else ""
                for column in range(table.columnCount())
            ]
        )
    return rows


def _select_product_details_row(win, product_name):
    for row in range(win.product_details_table.rowCount()):
        item = win.product_details_table.item(row, 0)
        if item is not None and item.text() == product_name:
            win.product_details_table.selectRow(row)
            return
    raise AssertionError(f"Could not find product details row for {product_name!r}")


def _set_reports_shift_selection(win, shift_ids):
    wanted = set(shift_ids)
    win.reports_shift_list.blockSignals(True)
    for index in range(win.reports_shift_list.count()):
        item = win.reports_shift_list.item(index)
        item.setSelected(item.data(QtCore.Qt.ItemDataRole.UserRole) in wanted)
    win.reports_shift_list.blockSignals(False)
    win.refresh_reports(refresh_shift_filter=False)


def test_inventory_add_and_list(tmp_path):
    db_file = tmp_path / "test.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    prod = inv.add_product("Apple", 0.99, category="beer", sub_category="Draught", font_size=12)
    assert prod.id is not None
    products = inv.list_products()
    assert len(products) == 1
    assert products[0].name == "Apple"
    assert products[0].category == "beer"
    assert products[0].sub_category == "Draught"
    assert products[0].font_size == 12

    # ensure decimal prices preserved and categories stored
    prod2 = inv.add_product("Gum", 1.23, category="spirits", sub_category="")
    assert prod2.price == pytest.approx(1.23)
    assert prod2.category == "spirits"
    assert prod2.sub_category == ""
    assert prod2.font_size == 10

    # test deletion
    inv.delete_product(prod.id)
    prods = inv.list_products()
    assert all(p.id != prod.id for p in prods)


def test_update_product_font_size(tmp_path):
    db_file = tmp_path / "font.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    product = inv.add_product("Juice", 2.50, category="snacks")
    product.font_size = 16
    inv.update_product(product)

    updated = inv.list_products()[0]
    assert updated.font_size == 16


def test_tile_order_persists(tmp_path):
    db_file = tmp_path / "tile_order.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    first = inv.add_product(
        "First",
        1.00,
        category="beer",
        sub_category="Draught",
        tile_order=2,
        tile_row=0,
        tile_column=1,
    )
    second = inv.add_product(
        "Second",
        1.10,
        category="beer",
        sub_category="Draught",
        tile_order=1,
        tile_row=0,
        tile_column=0,
    )

    products = inv.list_products()
    by_name = {product.name: product for product in products}
    assert by_name["First"].tile_order == 2
    assert by_name["Second"].tile_order == 1
    assert by_name["First"].tile_row == 0
    assert by_name["First"].tile_column == 1
    assert by_name["Second"].tile_row == 0
    assert by_name["Second"].tile_column == 0

    first.tile_order = 3
    first.tile_row = 1
    first.tile_column = 2
    inv.update_product(first)
    updated = {product.name: product for product in inv.list_products()}
    assert updated["First"].tile_order == 3
    assert updated["First"].tile_row == 1
    assert updated["First"].tile_column == 2


def test_explicit_grid_positions_display(tmp_path):
    try:
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "grid_positions.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    inv.add_product(
        "First",
        1.00,
        category="beer",
        sub_category="Draught",
        tile_row=0,
        tile_column=2,
    )
    inv.add_product(
        "Second",
        1.20,
        category="beer",
        sub_category="Draught",
        tile_row=1,
        tile_column=0,
    )

    win = MainWindow()
    win.inventory = inv
    win.current_category = "beer"
    win.current_subcategory = "Draught"
    win.refresh_products()

    positions = {}
    for index in range(win.product_layout.count()):
        item = win.product_layout.itemAt(index)
        widget = item.widget()
        row, column, _, _ = win.product_layout.getItemPosition(index)
        if widget is not None:
            positions[widget.text().splitlines()[0]] = (row, column)

    assert positions["First"] == (0, 2)
    assert positions["Second"] == (1, 0)


def test_grid_layout_width_tracks_configured_columns(tmp_path):
    try:
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "grid_width.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    for column in range(6):
        inv.add_product(
            f"Item {column + 1}",
            3.00 + column,
            category="beer",
            sub_category="Draught",
            tile_row=0,
            tile_column=column,
        )

    win = MainWindow()
    win.inventory = inv
    win.grid_columns = 6
    win.grid_rows = 6
    win.apply_grid_layout_settings()
    win.current_category = "beer"
    win.update_subcategories("beer")
    win.current_subcategory = "Draught"
    win.refresh_products()
    win.resize(1600, 900)
    win.show()
    QtWidgets.QApplication.processEvents()

    expected_board_width = _expected_board_width(win)
    frame_width = win.product_area.frameWidth() * 2
    scrollbar_extent = win.product_area.style().pixelMetric(
        QtWidgets.QStyle.PixelMetric.PM_ScrollBarExtent
    )

    assert win.product_container.minimumWidth() == expected_board_width
    assert win.product_container.maximumWidth() == expected_board_width
    assert win.product_container.width() == expected_board_width
    assert win.product_area.maximumWidth() == expected_board_width + frame_width + scrollbar_extent
    assert win.product_area.width() <= expected_board_width + frame_width + scrollbar_extent
    assert win.cat_widget.width() == expected_board_width + frame_width + scrollbar_extent
    assert win.subcat_widget.width() == expected_board_width + frame_width + scrollbar_extent


def test_cart_panel_has_right_side_delimiter_and_bottom_actions(tmp_path):
    try:
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "cart_panel_layout.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    inv.add_product("Tea", 2.00, category="Hot Drinks")

    win = MainWindow()
    win.inventory = inv
    win.current_category = "Hot Drinks"
    win.refresh_products()
    win.resize(1400, 900)
    win.show()
    QtWidgets.QApplication.processEvents()

    product_area_left = win.product_area.mapTo(win.till_tab, QtCore.QPoint(0, 0)).x()
    cart_delimiter_left = win.cart_delimiter.mapTo(win.till_tab, QtCore.QPoint(0, 0)).x()
    cart_panel_left = win.cart_panel.mapTo(win.till_tab, QtCore.QPoint(0, 0)).x()
    cart_button_panel_left = win.cart_button_panel.mapTo(win.till_tab, QtCore.QPoint(0, 0)).x()
    cart_button_panel_top = win.cart_button_panel.mapTo(win.till_tab, QtCore.QPoint(0, 0)).y()
    add_button_left = win.to_cart_button.mapTo(win.till_tab, QtCore.QPoint(0, 0)).x()
    add_button_top = win.to_cart_button.mapTo(win.till_tab, QtCore.QPoint(0, 0)).y()
    checkout_button_top = win.checkout_button.mapTo(win.till_tab, QtCore.QPoint(0, 0)).y()
    manager_top = win.manager_button.mapTo(win, QtCore.QPoint(0, 0)).y()
    manager_right = win.manager_button.mapTo(win, QtCore.QPoint(0, 0)).x() + win.manager_button.width()
    tab_bar_top = win.main_tabs.tabBar().mapTo(win, QtCore.QPoint(0, 0)).y()
    till_tab_size = win.main_tabs.tabBar().tabRect(0).size()
    till_tab_top = win.till_tab.mapTo(win, QtCore.QPoint(0, 0)).y()
    main_tabs_right = win.main_tabs.mapTo(win, QtCore.QPoint(0, 0)).x() + win.main_tabs.width()

    assert win.cart_panel.frameShape() == QtWidgets.QFrame.Shape.StyledPanel
    assert win.cart_delimiter.frameShape() == QtWidgets.QFrame.Shape.VLine
    assert win.cart_panel.minimumWidth() == 250
    assert win.cart_panel.maximumWidth() == 340
    assert win.cart_column.height() >= win.product_area.height() - 2
    assert win.cart_delimiter.height() >= win.product_area.height() - 2
    assert cart_panel_left > product_area_left + win.product_area.width()
    assert cart_delimiter_left > product_area_left + win.product_area.width()
    assert cart_button_panel_left == cart_panel_left
    assert win.cart_button_panel.width() == win.cart_panel.width()
    assert add_button_left == cart_button_panel_left
    assert win.to_cart_button.width() == win.cart_button_panel.width()
    assert add_button_top >= cart_button_panel_top
    assert win.remove_button.width() == win.cart_button_panel.width()
    assert win.checkout_button.width() == win.cart_button_panel.width()
    assert win.remove_button.y() > win.to_cart_button.y() + win.to_cart_button.height() - 1
    assert win.checkout_button.y() > win.remove_button.y() + win.remove_button.height() - 1
    assert win.cart_button_panel.y() > win.cart_panel.y() + win.cart_panel.height() - 1
    assert checkout_button_top >= cart_button_panel_top
    assert manager_top >= tab_bar_top
    assert manager_top < till_tab_top
    assert manager_right <= main_tabs_right
    assert win.manager_button.width() == till_tab_size.width()
    assert win.manager_button.height() == till_tab_size.height()


def test_bills_panels_use_compact_widths(tmp_path):
    try:
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "bills_compact_widths.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    inv.add_product("Tea", 2.00, category="Hot Drinks")

    win = MainWindow()
    win.inventory = inv
    win.refresh_bills()

    assert win.bills_list.minimumWidth() == 380
    assert win.bill_detail.minimumWidth() == 380
    assert win.bills_content_layout.spacing() == 8
    assert win.close_day_button.width() == 84
    assert win.shift_report_button.width() == 108


def test_reports_panels_use_compact_widths(tmp_path):
    try:
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "reports_compact_widths.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    inv.add_product("Tea", 2.00, category="Hot Drinks")

    win = MainWindow()
    win.inventory = inv
    win.refresh_reports()

    assert win.reports_shift_list.minimumWidth() == 300


def test_filter_required(tmp_path, monkeypatch):
    # if no category selected, the product list shows placeholder
    try:
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")
    db_file = tmp_path / "test.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    inv.add_product("Cola", 0.50, category="beer", sub_category="Bottled")
    # also exercise snack category
    inv.add_product("Chips", 1.00, category="snacks")
    prods = inv.list_products()
    assert any(p.category == "snacks" for p in prods)
    win = MainWindow()
    win.inventory = inv
    win.current_category = None
    win.refresh_products()
    # expect a single placeholder widget
    assert win.product_layout.count() == 1
    widget = win.product_layout.itemAt(0).widget()
    assert widget and "select category" in widget.text().lower()


def test_category_and_subcategory_buttons_are_compact_and_delimited(tmp_path):
    try:
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "filter_buttons.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    inv.add_product("Lager", 3.00, category="Beer", sub_category="Draught")

    win = MainWindow()
    win.inventory = inv
    win.rebuild_category_buttons()
    win.update_subcategories("Beer")

    beer_button = next(
        button for label, button in win.category_buttons.items() if label.lower() == "beer"
    )
    draught_button = next(
        button for label, button in win.subcategory_buttons.items() if label.lower() == "draught"
    )

    for button in (beer_button, draught_button):
        style = button.styleSheet().lower()
        assert button.maximumHeight() == 32
        assert button.sizeHint().height() <= 38
        assert "font-size: 9pt" in style
        assert "border: 1px solid" in style
        assert "background-color" in style
def test_category_without_subcategory_displays_items(tmp_path):
    try:
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "hot_drinks.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    inv.add_product("Latte", 2.80, category="hot drinks")

    win = MainWindow()
    win.inventory = inv
    win.current_category = "hot drinks"
    win.current_subcategory = None
    win.refresh_products()

    assert win.product_layout.count() == 1
    widget = win.product_layout.itemAt(0).widget()
    assert widget is not None
    assert "latte" in widget.text().lower()


def test_subcategory_filter(tmp_path, monkeypatch):
    try:
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")
    db_file = tmp_path / "test.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    inv.add_product("Lager", 3.00, category="Beer", sub_category="Draught")
    inv.add_product("Ale", 3.50, category="Beer", sub_category="Bottled")
    win = MainWindow()
    win.inventory = inv
    # stub out pin check so UI actions can run
    win.check_pin = lambda: True
    # select category but no subcategory -> placeholder
    win.current_category = "Beer"
    win.update_subcategories("Beer")
    win.refresh_products()
    assert any("select subcategory" in text for text in _layout_texts(win.product_layout))
    # test editing: directly set selected id and call edit
    prod = next(product for product in inv.list_products() if product.name == "Lager")
    win.selected_product_id = prod.id
    win.choose_product_from_inventory = lambda *args, **kwargs: prod
    # monkeypatch dialogs by overriding QInputDialog methods to return new values
    original_getText = QtWidgets.QInputDialog.getText
    original_getDouble = QtWidgets.QInputDialog.getDouble
    original_getItem = QtWidgets.QInputDialog.getItem
    QtWidgets.QInputDialog.getText = staticmethod(lambda *args, **kwargs: ("NewName", True))
    QtWidgets.QInputDialog.getDouble = staticmethod(lambda *args, **kwargs: (5.55, True))
    def fake_getItem(*args, **kwargs):
        title = args[1] if len(args) > 1 else kwargs.get("title", "")
        if title == "Category":
            return ("Beer", True)
        if title == "Subcategory":
            return ("Draught", True)
        return ("", False)

    QtWidgets.QInputDialog.getItem = staticmethod(fake_getItem)
    win.edit_selected_product()
    # restore originals
    QtWidgets.QInputDialog.getText = original_getText
    QtWidgets.QInputDialog.getDouble = original_getDouble
    QtWidgets.QInputDialog.getItem = original_getItem
    # verify change saved
    updated = next(product for product in inv.list_products() if product.id == prod.id)
    assert updated.name == "NewName"
    assert updated.price == pytest.approx(5.55)
    # now choose subcategory Draught
    win.select_subcategory("Draught", True)
    draught_texts = _layout_texts(win.product_layout)
    assert any("newname" in text for text in draught_texts)
    # text should not include id or category tags
    assert all("beer" not in text for text in draught_texts)
    assert all("draught" not in text for text in draught_texts)
    # switch to bottled
    win.select_subcategory("Bottled", True)
    bottled_texts = _layout_texts(win.product_layout)
    assert any("ale" in text for text in bottled_texts)
    assert all("beer" not in text for text in bottled_texts)
    assert all("bottled" not in text for text in bottled_texts)


def test_currency_symbol_in_list(tmp_path, monkeypatch):
    # ensure view displays £ symbol; skip if PyQt6 not installed
    try:
        from interface.till.views import MainWindow, CURRENCY
    except ImportError:
        pytest.skip("PyQt6 not available")
    db_file = tmp_path / "test.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    inv.add_product("Tea", 1.50, category="hot drinks")
    win = MainWindow()
    # but we can't show window; just call refresh_products
    win.inventory = inv
    win.current_category = "hot drinks"
    win.refresh_products()
    # look at widgets in product_layout
    found = False
    for i in range(win.product_layout.count()):
        w = win.product_layout.itemAt(i).widget()
        if w and CURRENCY in w.text():
            found = True
            break
    assert found


def test_product_details_tab_lists_all_products_with_separate_category_columns(tmp_path):
    try:
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "product_details.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    inv.add_product("Lager", 3.20, category="Beer", sub_category="Draught")
    inv.add_product("Tea", 1.50, category="Hot Drinks")
    inv.add_product("Water", 1.00)

    win = MainWindow()
    win.inventory = inv
    win.current_category = "Beer"
    win.current_subcategory = "Draught"
    win.refresh_products()

    tab_labels = [win.main_tabs.tabText(index) for index in range(win.main_tabs.count())]
    assert tab_labels == ["Till", "Bills", "Product Details", "Reports"]
    tab_style = win.styleSheet().lower()
    assert "qtabbar::tab:selected" in tab_style
    assert "background-color: #3f6b3f" in tab_style
    assert "border-color: #80b780" in tab_style

    assert win.product_layout.count() == 1
    assert win.product_details_table.horizontalHeaderItem(0).text() == "Name"
    assert win.product_details_table.horizontalHeaderItem(1).text() == "Price"
    assert win.product_details_table.horizontalHeaderItem(2).text() == "Category"
    assert win.product_details_table.horizontalHeaderItem(3).text() == "Subcategory"
    assert win.product_details_table.rowCount() == 3
    assert win.product_details_count_label.text() == "3 products"

    rows_by_name = {row[0]: row for row in _table_rows(win.product_details_table)}
    assert rows_by_name["Lager"] == ["Lager", "£3.20", "Beer", "Draught"]
    assert rows_by_name["Tea"] == ["Tea", "£1.50", "Hot Drinks", ""]
    assert rows_by_name["Water"] == ["Water", "£1.00", "Uncategorised", ""]


def test_product_details_search_filters_table_without_affecting_till_grid(tmp_path):
    try:
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "product_details_search.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    inv.add_product("Lager", 3.20, category="Beer", sub_category="Draught")
    inv.add_product("Ale", 3.40, category="Beer", sub_category="Bottled")
    inv.add_product("Tea", 1.50, category="Hot Drinks")
    inv.add_product("Water", 1.00)

    win = MainWindow()
    win.inventory = inv
    win.current_category = "Beer"
    win.current_subcategory = "Draught"
    win.refresh_products()

    assert win.product_layout.count() == 1
    assert win.product_details_table.rowCount() == 4

    win.product_details_search.setText("hot")

    rows = _table_rows(win.product_details_table)
    assert rows == [["Tea", "£1.50", "Hot Drinks", ""]]
    assert win.product_details_count_label.text() == "Showing 1 of 4 products"
    assert win.product_layout.count() == 1
    till_widget = win.product_layout.itemAt(0).widget()
    assert till_widget is not None
    assert "lager" in till_widget.text().lower()

    win.product_details_search.setText("3.40")
    rows = _table_rows(win.product_details_table)
    assert rows == [["Ale", "£3.40", "Beer", "Bottled"]]

    win.product_details_search.clear()
    index = win.product_details_category_filter.findText("Uncategorised")
    assert index >= 0
    win.product_details_category_filter.setCurrentIndex(index)

    rows = _table_rows(win.product_details_table)
    assert rows == [["Water", "£1.00", "Uncategorised", ""]]
    assert win.product_details_count_label.text() == "Showing 1 of 4 products"

    win.product_details_category_filter.setCurrentIndex(0)
    assert win.product_details_table.rowCount() == 4
    assert win.product_details_count_label.text() == "4 products"


def test_product_details_layout_remains_usable_in_compact_mode(tmp_path):
    try:
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "product_details_touch.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    inv.add_product("Coffee", 2.50, category="Hot Drinks")

    win = MainWindow()
    win.inventory = inv
    win.refresh_products()

    assert win.product_details_search.minimumHeight() >= 40
    assert win.product_details_category_filter.minimumHeight() >= 40
    assert win.product_details_add_button.minimumHeight() >= 40
    assert win.product_details_edit_button.minimumHeight() >= 40
    assert win.product_details_delete_button.minimumHeight() >= 40
    assert win.product_details_table.verticalHeader().defaultSectionSize() >= 40
    assert win.product_details_table.horizontalHeader().height() >= 38


def test_product_details_actions_refresh_table(tmp_path, monkeypatch):
    try:
        from interface.till import views as views_module
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "product_details_actions.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    inv.add_product("Coffee", 2.50, category="Hot Drinks")

    win = MainWindow()
    win.inventory = inv
    win.check_pin = lambda: True
    win.refresh_products()

    monkeypatch.setattr(
        views_module,
        "prompt_new_product",
        lambda *args, **kwargs: Product(
            name="Latte",
            price=3.75,
            category="Hot Drinks",
            sub_category="",
        ),
    )

    win.product_details_add_button.click()

    added_rows = {row[0]: row for row in _table_rows(win.product_details_table)}
    assert added_rows["Latte"] == ["Latte", "£3.75", "Hot Drinks", ""]
    assert win.product_details_table.rowCount() == 2

    _select_product_details_row(win, "Coffee")
    monkeypatch.setattr(
        views_module,
        "prompt_edit_product",
        lambda *args, **kwargs: Product(
            name="Flat White",
            price=2.80,
            category="Hot Drinks",
            sub_category="",
        ),
    )

    win.product_details_edit_button.click()

    edited_rows = {row[0]: row for row in _table_rows(win.product_details_table)}
    assert "Coffee" not in edited_rows
    assert edited_rows["Flat White"] == ["Flat White", "£2.80", "Hot Drinks", ""]

    _select_product_details_row(win, "Flat White")
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "question",
        staticmethod(lambda *args, **kwargs: QtWidgets.QMessageBox.StandardButton.Yes),
    )

    win.product_details_delete_button.click()

    remaining_rows = {row[0]: row for row in _table_rows(win.product_details_table)}
    assert "Flat White" not in remaining_rows
    assert remaining_rows["Latte"] == ["Latte", "£3.75", "Hot Drinks", ""]
    assert win.product_details_table.rowCount() == 1


def test_product_details_add_allows_blank_category(tmp_path, monkeypatch):
    try:
        from interface.till import views as views_module
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "product_details_blank_category.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    inv.add_product("Coffee", 2.50, category="Hot Drinks")

    win = MainWindow()
    win.inventory = inv
    win.check_pin = lambda: True
    win.refresh_products()

    call_kwargs = {}

    def fake_prompt_new_product(*args, **kwargs):
        call_kwargs.update(kwargs)
        return Product(
            name="Water",
            price=1.25,
            category="",
            sub_category="",
        )

    monkeypatch.setattr(views_module, "prompt_new_product", fake_prompt_new_product)

    win.product_details_add_button.click()

    assert call_kwargs.get("allow_empty_category") is True
    added_rows = {row[0]: row for row in _table_rows(win.product_details_table)}
    assert added_rows["Water"] == ["Water", "£1.25", "Uncategorised", ""]
    assert "Uncategorised" not in win.category_buttons

    stored = next(product for product in inv.list_products() if product.name == "Water")
    assert stored.category == ""
    assert stored.sub_category == ""


def test_product_details_edit_can_move_product_to_uncategorised(tmp_path, monkeypatch):
    try:
        from interface.till import views as views_module
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "product_details_edit_uncategorised.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    inv.add_product("Tea", 1.50, category="Hot Drinks")

    win = MainWindow()
    win.inventory = inv
    win.check_pin = lambda: True
    win.current_category = "Hot Drinks"
    win.refresh_products()

    _select_product_details_row(win, "Tea")

    call_kwargs = {}

    def fake_prompt_edit_product(*args, **kwargs):
        call_kwargs.update(kwargs)
        return Product(
            name="Tea",
            price=1.50,
            category="",
            sub_category="",
        )

    monkeypatch.setattr(views_module, "prompt_edit_product", fake_prompt_edit_product)

    win.product_details_edit_button.click()

    assert call_kwargs.get("allow_empty_category") is True
    assert win.product_layout.count() == 0
    assert not win.get_visible_products()

    index = win.product_details_category_filter.findText("Uncategorised")
    assert index >= 0
    win.product_details_category_filter.setCurrentIndex(index)

    rows = _table_rows(win.product_details_table)
    assert rows == [["Tea", "£1.50", "Uncategorised", ""]]

    stored = next(product for product in inv.list_products() if product.name == "Tea")
    assert stored.category == ""
    assert stored.sub_category == ""


def test_manager_dialog_exposes_database_inspector_action(tmp_path, monkeypatch):
    try:
        from interface.till import views as views_module
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "manager_actions.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    inv.add_product("Coffee", 2.50, category="Hot Drinks")

    win = MainWindow()
    win.inventory = inv
    win.check_pin = lambda: True

    captured = {}
    opened = []

    monkeypatch.setattr(
        views_module,
        "show_manager_dialog",
        lambda parent, product_actions, design_actions: captured.update(
            product_actions=product_actions,
            design_actions=design_actions,
        ),
    )
    monkeypatch.setattr(win, "open_database_inspector", lambda require_pin=True: opened.append(require_pin))

    win.open_manager_dialog()

    assert "Database Inspector" in captured["product_actions"]
    captured["product_actions"]["Database Inspector"]()
    assert opened == [False]


def test_database_inspector_dialog_shows_live_database_snapshot(tmp_path):
    try:
        from interface.till.database_inspector_dialog import build_database_inspector_dialog
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "database_inspector.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    tea = inv.add_product("Tea", 2.00, category="Hot Drinks")
    cake = inv.add_product("Cake", 4.00, category="Snacks")

    first_cart = CartController(db=db)
    first_cart.add_item(tea)
    first_cart.checkout(payment_method="Cash")
    _, open_shift = db.close_current_shift()

    second_cart = CartController(db=db)
    second_cart.add_item(tea)
    second_cart.add_item(cake)
    second_txn = second_cart.checkout(payment_method="Visa")
    db.update_transaction(
        Transaction(
            id=second_txn.id,
            payment_method="Mastercard",
            timestamp=datetime.datetime(2026, 3, 11, 18, 45, 0),
            items=[
                TransactionItem(
                    product_id=tea.id,
                    product_name="Tea",
                    unit_price=2.00,
                    quantity=1,
                    category="Hot Drinks",
                    sub_category="",
                )
            ],
        )
    )

    dialog = build_database_inspector_dialog(None, db)

    assert dialog.database_path_value.text().endswith("database_inspector.db")
    assert dialog.product_count_value.text() == "2"
    assert dialog.transaction_count_value.text() == "2"
    assert dialog.shift_count_value.text() == "2"
    assert dialog.open_shift_value.text() == f"#{open_shift.id}"
    assert dialog.backup_count_value.text() == "0"
    assert dialog.audit_count_value.text() == "1"
    assert dialog.products_table.rowCount() == 2
    assert dialog.transactions_table.rowCount() == 2
    assert dialog.transaction_items_table.rowCount() == 2
    assert dialog.shifts_table.rowCount() == 2
    assert dialog.audit_table.rowCount() == 1

    transaction_rows = {row[0]: row for row in _table_rows(dialog.transactions_table)}
    assert transaction_rows[str(second_txn.id)][3] == "Mastercard"
    assert transaction_rows[str(second_txn.id)][4] == "£2.00"

    transaction_item_rows = [row for row in _table_rows(dialog.transaction_items_table) if row[0] == str(second_txn.id)]
    assert len(transaction_item_rows) == 1
    assert transaction_item_rows[0][2] == str(open_shift.id)
    assert transaction_item_rows[0][4] == "Tea"
    assert transaction_item_rows[0][7] == "£2.00"
    assert transaction_item_rows[0][8] == "1"
    assert transaction_item_rows[0][9] == "£2.00"

    audit_rows = _table_rows(dialog.audit_table)
    assert audit_rows[0][0] == str(second_txn.id)
    assert audit_rows[0][1] == str(open_shift.id)
    assert audit_rows[0][3] == "#1"
    assert "Visa" in audit_rows[0][4]
    assert "Mastercard" in audit_rows[0][5]
    assert "Removed: Cake x1 @ £4.00 = £4.00" in audit_rows[0][6]

    shift_rows = _table_rows(dialog.shifts_table)
    assert shift_rows[0][0] == str(open_shift.id)
    assert shift_rows[0][1] == "Open"


def test_cart_add_and_checkout(tmp_path, monkeypatch):
    # use a temporary database
    db_file = tmp_path / "test2.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    prod = inv.add_product("Banana", 0.50)
    cart = CartController(db=db)
    cart.add_item(prod, quantity=2)
    assert cart.total() == 1.0
    txn = cart.checkout()
    assert txn.total == 1.0
    # ensure database recorded
    db2 = Database(path=db_file)
    prods = db2.list_products()
    assert len(prods) == 1


def test_checkout_persists_payment_method_and_item_snapshot(tmp_path):
    db_file = tmp_path / "history.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    prod = inv.add_product("Banana", 0.50, category="Snacks")

    cart = CartController(db=db)
    cart.add_item(prod, quantity=2)
    txn = cart.checkout(payment_method="Visa")

    assert txn.id is not None
    assert txn.payment_method == "Visa"
    assert txn.items[0].product_name == "Banana"
    assert txn.items[0].unit_price == pytest.approx(0.50)
    assert txn.items[0].quantity == 2

    stored = db.get_transaction(txn.id)
    assert stored is not None
    assert stored.payment_method == "Visa"
    assert stored.shift_id is not None
    assert stored.total == pytest.approx(1.0)
    assert stored.items[0].product_name == "Banana"
    assert stored.items[0].unit_price == pytest.approx(0.50)
    assert stored.items[0].line_total == pytest.approx(1.0)


def test_transaction_snapshot_survives_later_product_changes(tmp_path):
    db_file = tmp_path / "snapshot.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    prod = inv.add_product("Tea", 1.50, category="Hot Drinks")

    cart = CartController(db=db)
    cart.add_item(prod)
    txn = cart.checkout(payment_method="Cash")

    prod.price = 2.75
    prod.name = "Large Tea"
    inv.update_product(prod)

    stored = db.get_transaction(txn.id)
    assert stored is not None
    assert stored.items[0].product_name == "Tea"
    assert stored.items[0].unit_price == pytest.approx(1.50)


def test_update_transaction_changes_saved_bill_and_shift_summary(tmp_path):
    db_file = tmp_path / "edit_bill.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    prod = inv.add_product("Coffee", 2.50, category="Hot Drinks")

    cart = CartController(db=db)
    cart.add_item(prod, quantity=2)
    txn = cart.checkout(payment_method="Cash")

    db.update_transaction(
        Transaction(
            id=txn.id,
            payment_method="Visa",
            timestamp=datetime.datetime(2026, 3, 10, 11, 45, 0),
            items=[
                TransactionItem(
                    product_id=prod.id,
                    product_name="Large Coffee",
                    unit_price=3.00,
                    quantity=3,
                    category="Hot Drinks",
                    sub_category="",
                )
            ],
        )
    )

    stored = db.get_transaction(txn.id)
    assert stored is not None
    assert stored.payment_method == "Visa"
    assert stored.total == pytest.approx(9.0)
    assert stored.timestamp == datetime.datetime(2026, 3, 10, 11, 45, 0)
    assert stored.edited_at is not None
    assert stored.items[0].product_name == "Large Coffee"
    assert stored.items[0].line_total == pytest.approx(9.0)

    summary = db.get_shift_summary(stored.shift_id)
    assert summary["cash_total"] == pytest.approx(0.0)
    assert summary["card_total"] == pytest.approx(9.0)
    assert summary["visa_total"] == pytest.approx(9.0)
    assert summary["total"] == pytest.approx(9.0)

    revisions = db.list_transaction_revisions(txn.id)
    assert len(revisions) == 1
    assert revisions[0].transaction_id == txn.id
    assert revisions[0].payment_method == "Cash"
    assert revisions[0].timestamp == txn.timestamp
    assert revisions[0].edited_at is None
    assert [item.product_name for item in revisions[0].items] == ["Coffee"]
    assert revisions[0].items[0].quantity == 2
    assert revisions[0].items[0].unit_price == pytest.approx(2.50)


def test_timestamped_backups_rotate_old_files(tmp_path):
    db_file = tmp_path / "backup_rotation.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)

    inv.add_product("Tea", 2.00, category="Hot Drinks")
    first_backup = db.backups.create_timestamped_backup(keep=2)

    inv.add_product("Coffee", 2.50, category="Hot Drinks")
    second_backup = db.backups.create_timestamped_backup(keep=2)

    inv.add_product("Cake", 3.00, category="Snacks")
    third_backup = db.backups.create_timestamped_backup(keep=2)

    backups = db.backups.list_backups()
    assert backups == [third_backup, second_backup]
    assert first_backup not in backups
    assert not first_backup.exists()
    assert third_backup.parent == db.backups.manual_backup_dir


def test_restore_from_backup_replaces_live_data_and_reopens_connection(tmp_path):
    db_file = tmp_path / "backup_restore.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)

    inv.add_product("Tea", 2.00, category="Hot Drinks")
    backup_path = db.backups.create_timestamped_backup()

    inv.add_product("Cake", 3.00, category="Snacks")
    assert sorted(product.name for product in inv.list_products()) == ["Cake", "Tea"]

    safety_backup = db.backups.restore_from_backup(backup_path)

    restored_products = db.list_products()
    assert [product.name for product in restored_products] == ["Tea"]
    assert db.conn is not None
    assert backup_path.parent == db.backups.manual_backup_dir
    assert safety_backup.exists()
    assert safety_backup.parent == db.backups.restore_safety_backup_dir
    assert ".pre_restore." in safety_backup.name


def test_record_transaction_rolls_back_when_item_insert_fails(tmp_path):
    db_file = tmp_path / "record_transaction_rollback.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    prod = inv.add_product("Coffee", 2.50, category="Hot Drinks")

    with pytest.raises(sqlite3.IntegrityError):
        db.record_transaction(
            Transaction(
                payment_method="Cash",
                items=[
                    TransactionItem(
                        product_id=prod.id,
                        product_name="Coffee",
                        unit_price=2.50,
                        quantity=1,
                        category="Hot Drinks",
                        sub_category="",
                    ),
                    TransactionItem(
                        product_id=999999,
                        product_name="Missing Product",
                        unit_price=1.00,
                        quantity=1,
                        category="Hot Drinks",
                        sub_category="",
                    ),
                ],
            )
        )

    assert db.list_transactions() == []
    assert db.conn.execute("SELECT COUNT(*) FROM transaction_items").fetchone()[0] == 0
    assert db.get_open_shift_summary()["count"] == 0


def test_update_transaction_rolls_back_when_item_insert_fails(tmp_path):
    db_file = tmp_path / "update_transaction_rollback.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    prod = inv.add_product("Tea", 2.00, category="Hot Drinks")

    cart = CartController(db=db)
    cart.add_item(prod)
    txn = cart.checkout(payment_method="Cash")

    original = db.get_transaction(txn.id)

    with pytest.raises(sqlite3.IntegrityError):
        db.update_transaction(
            Transaction(
                id=txn.id,
                payment_method="Visa",
                timestamp=datetime.datetime(2026, 3, 10, 12, 0, 0),
                items=[
                    TransactionItem(
                        product_id=prod.id,
                        product_name="Tea",
                        unit_price=2.00,
                        quantity=1,
                        category="Hot Drinks",
                        sub_category="",
                    ),
                    TransactionItem(
                        product_id=999999,
                        product_name="Broken Line",
                        unit_price=1.00,
                        quantity=1,
                        category="Hot Drinks",
                        sub_category="",
                    ),
                ],
            )
        )

    stored = db.get_transaction(txn.id)
    assert stored is not None
    assert stored.payment_method == original.payment_method
    assert stored.total == pytest.approx(original.total)
    assert stored.timestamp == original.timestamp
    assert stored.edited_at is None
    assert len(stored.items) == 1
    assert stored.items[0].product_name == original.items[0].product_name

    summary = db.get_shift_summary(stored.shift_id)
    assert summary["cash_total"] == pytest.approx(original.total)
    assert summary["card_total"] == pytest.approx(0.0)
    assert db.list_transaction_revisions(txn.id) == []


def test_update_transaction_keeps_multiple_saved_revisions(tmp_path):
    db_file = tmp_path / "edit_bill_revisions.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    coffee = inv.add_product("Coffee", 2.50, category="Hot Drinks")
    cake = inv.add_product("Cake", 4.00, category="Snacks")

    cart = CartController(db=db)
    cart.add_item(coffee)
    cart.add_item(cake)
    txn = cart.checkout(payment_method="Cash")

    first_edit_time = datetime.datetime(2026, 3, 10, 15, 0, 0)
    db.update_transaction(
        Transaction(
            id=txn.id,
            payment_method="Visa",
            timestamp=first_edit_time,
            items=[
                TransactionItem(
                    product_id=coffee.id,
                    product_name="Coffee",
                    unit_price=2.50,
                    quantity=2,
                    category="Hot Drinks",
                    sub_category="",
                )
            ],
        )
    )

    second_edit_time = datetime.datetime(2026, 3, 10, 16, 30, 0)
    db.update_transaction(
        Transaction(
            id=txn.id,
            payment_method="Mastercard",
            timestamp=second_edit_time,
            items=[
                TransactionItem(
                    product_id=coffee.id,
                    product_name="Mocha",
                    unit_price=4.50,
                    quantity=1,
                    category="Hot Drinks",
                    sub_category="",
                )
            ],
        )
    )

    revisions = db.list_transaction_revisions(txn.id)
    assert len(revisions) == 2

    original_revision, first_saved_revision = revisions
    assert original_revision.payment_method == "Cash"
    assert [item.product_name for item in original_revision.items] == ["Coffee", "Cake"]
    assert original_revision.edited_at is None

    assert first_saved_revision.payment_method == "Visa"
    assert first_saved_revision.timestamp == first_edit_time
    assert first_saved_revision.edited_at is not None
    assert [item.product_name for item in first_saved_revision.items] == ["Coffee"]
    assert first_saved_revision.items[0].quantity == 2


def test_close_current_shift_rolls_back_when_new_shift_creation_fails(tmp_path, monkeypatch):
    db_file = tmp_path / "close_shift_rollback.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    prod = inv.add_product("Water", 1.50, category="Snacks")

    cart = CartController(db=db)
    cart.add_item(prod)
    cart.checkout(payment_method="Cash")

    current_shift = db.get_or_create_open_shift()
    monkeypatch.setattr(
        db,
        "_create_shift",
        lambda opened_at=None, commit=True: (_ for _ in ()).throw(RuntimeError("shift create failed")),
    )

    with pytest.raises(RuntimeError, match="shift create failed"):
        db.close_current_shift()

    stored_shift = db.get_shift(current_shift.id)
    assert stored_shift is not None
    assert stored_shift.closed_at is None
    assert db.get_open_shift_summary()["shift_id"] == current_shift.id


def test_daily_summary_groups_payment_methods(tmp_path):
    db_file = tmp_path / "summary.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    apple = inv.add_product("Apple", 1.00)
    juice = inv.add_product("Juice", 2.50)

    cash_cart = CartController(db=db)
    cash_cart.add_item(apple, quantity=2)
    cash_cart.checkout(payment_method="Cash")

    visa_cart = CartController(db=db)
    visa_cart.add_item(juice)
    visa_cart.checkout(payment_method="Visa")

    amex_cart = CartController(db=db)
    amex_cart.add_item(apple)
    amex_cart.checkout(payment_method="Amex")

    summary = db.get_daily_summary()

    assert summary["count"] == 3
    assert summary["cash_total"] == pytest.approx(2.0)
    assert summary["card_total"] == pytest.approx(3.5)
    assert summary["visa_total"] == pytest.approx(2.5)
    assert summary["mastercard_total"] == pytest.approx(0.0)
    assert summary["amex_total"] == pytest.approx(1.0)
    assert summary["total"] == pytest.approx(5.5)


def test_checkout_assigns_current_open_shift(tmp_path):
    db_file = tmp_path / "shift_assign.db"
    db = Database(path=db_file)
    shift = db.get_or_create_open_shift()
    inv = InventoryController(db=db)
    prod = inv.add_product("Water", 1.20)

    cart = CartController(db=db)
    cart.add_item(prod)
    txn = cart.checkout(payment_method="Cash")

    stored = db.get_transaction(txn.id)
    assert stored is not None
    assert stored.shift_id == shift.id
    open_summary = db.get_open_shift_summary()
    assert open_summary["shift_id"] == shift.id
    assert open_summary["count"] == 1


def test_legacy_transactions_are_backfilled_into_closed_shifts(tmp_path):
    db_file = tmp_path / "legacy_shift_migration.db"
    db = Database(path=db_file)

    connection = db.conn
    connection.execute("INSERT INTO products (name, price) VALUES ('Old Tea', 2.0)")
    product_id = connection.execute("SELECT id FROM products WHERE name = 'Old Tea'").fetchone()[0]
    connection.execute(
        "INSERT INTO transactions (total, timestamp, payment_method, shift_id) VALUES (?, ?, ?, NULL)",
        (2.0, "2026-03-09T10:00:00", "Cash"),
    )
    transaction_id = connection.execute("SELECT max(id) FROM transactions").fetchone()[0]
    connection.execute(
        """
        INSERT INTO transaction_items (transaction_id, product_id, quantity, product_name, unit_price, category, sub_category)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (transaction_id, product_id, 1, "Old Tea", 2.0, "Hot Drinks", ""),
    )
    connection.commit()

    migrated_db = Database(path=db_file)
    transactions = migrated_db.list_transactions()
    assert len(transactions) == 1
    assert transactions[0].shift_id is not None

    shifts = migrated_db.list_shifts()
    migrated_shift = next(shift for shift in shifts if shift.closed_at is not None)
    summary = migrated_db.get_shift_summary(migrated_shift.id)
    assert summary["count"] == 1
    assert summary["cash_total"] == pytest.approx(2.0)


def test_close_current_shift_preserves_history_and_opens_new_shift(tmp_path):
    db_file = tmp_path / "shift_close.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    prod = inv.add_product("Coffee", 2.00)

    cart = CartController(db=db)
    cart.add_item(prod, quantity=2)
    txn = cart.checkout(payment_method="Mastercard")

    original_shift = db.get_or_create_open_shift()
    closed_shift, new_shift = db.close_current_shift()

    assert closed_shift.id == original_shift.id
    assert closed_shift.closed_at is not None
    assert new_shift.id != closed_shift.id
    assert new_shift.closed_at is None

    stored = db.get_transaction(txn.id)
    assert stored is not None
    assert stored.shift_id == closed_shift.id
    assert len(db.list_transactions()) == 1

    closed_summary = db.get_shift_summary(closed_shift.id)
    assert closed_summary["count"] == 1
    assert closed_summary["card_total"] == pytest.approx(4.0)
    assert closed_summary["mastercard_total"] == pytest.approx(4.0)

    new_summary = db.get_open_shift_summary()
    assert new_summary["shift_id"] == new_shift.id
    assert new_summary["count"] == 0


def test_database_can_aggregate_item_sales_by_shift_and_time_range(tmp_path):
    db_file = tmp_path / "reports_aggregate.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    tea = inv.add_product("Tea", 2.00, category="Hot Drinks")
    cake = inv.add_product("Cake", 4.00, category="Snacks")

    first_cart = CartController(db=db)
    first_cart.add_item(tea, quantity=1)
    first_txn = first_cart.checkout(payment_method="Cash")
    db.update_transaction(
        Transaction(
            id=first_txn.id,
            payment_method=first_txn.payment_method,
            timestamp=datetime.datetime(2026, 3, 10, 9, 0, 0),
            items=first_txn.items,
        )
    )
    closed_shift, open_shift = db.close_current_shift(
        closed_at=datetime.datetime(2026, 3, 10, 10, 0, 0)
    )

    second_cart = CartController(db=db)
    second_cart.add_item(tea, quantity=2)
    second_cart.add_item(cake, quantity=1)
    second_txn = second_cart.checkout(payment_method="Visa")
    db.update_transaction(
        Transaction(
            id=second_txn.id,
            payment_method=second_txn.payment_method,
            timestamp=datetime.datetime(2026, 3, 11, 9, 0, 0),
            items=second_txn.items,
        )
    )

    closed_shift_rows = {
        item.product_name: item for item in db.list_item_sales(shift_ids=[closed_shift.id])
    }
    assert closed_shift_rows["Tea"].quantity_sold == 1
    assert closed_shift_rows["Tea"].revenue == pytest.approx(2.0)

    all_shift_rows = {
        item.product_name: item
        for item in db.list_item_sales(shift_ids=[closed_shift.id, open_shift.id])
    }
    assert all_shift_rows["Tea"].quantity_sold == 3
    assert all_shift_rows["Tea"].revenue == pytest.approx(6.0)
    assert all_shift_rows["Tea"].transaction_count == 2
    assert all_shift_rows["Cake"].quantity_sold == 1
    assert all_shift_rows["Cake"].revenue == pytest.approx(4.0)

    date_filtered_rows = {
        item.product_name: item
        for item in db.list_item_sales(
            start_at=datetime.datetime(2026, 3, 11, 0, 0, 0),
            end_at=datetime.datetime(2026, 3, 11, 23, 59, 59),
        )
    }
    assert set(date_filtered_rows) == {"Tea", "Cake"}
    assert date_filtered_rows["Tea"].quantity_sold == 2
    assert date_filtered_rows["Cake"].quantity_sold == 1


def test_bills_list_refreshes_after_checkout(tmp_path):
    try:
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "bills_ui.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    prod = inv.add_product("Coffee", 2.50, category="Hot Drinks")

    win = MainWindow()
    win.inventory = inv
    win.cart = CartController(db=db)
    win.refresh_bills()
    assert win.bills_list.count() == 0

    win.cart.add_item(prod, quantity=2)
    win.refresh_cart()
    win.choose_payment_method = lambda: "Visa"
    win.show_receipt_dialog = lambda *args, **kwargs: None

    win.perform_checkout()

    assert win.bills_list.count() == 1
    assert "Visa" in win.bills_list.item(0).text()
    assert "EDITED" not in win.bills_list.item(0).text()
    assert win.bill_status_badge.isHidden()
    assert "coffee" in win.bill_detail.toPlainText().lower()
    assert "total: £5.00".lower() in win.bill_detail.toPlainText().lower()
    assert win.bill_audit_group.isHidden()
    assert len(db.backups.list_backups()) == 1


def test_reports_tab_defaults_to_current_open_session(tmp_path):
    try:
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "reports_default_ui.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    tea = inv.add_product("Tea", 2.00, category="Hot Drinks")
    cake = inv.add_product("Cake", 4.00, category="Snacks")

    first_cart = CartController(db=db)
    first_cart.add_item(tea)
    first_cart.checkout(payment_method="Cash")
    _, open_shift = db.close_current_shift()

    second_cart = CartController(db=db)
    second_cart.add_item(cake)
    second_cart.checkout(payment_method="Visa")

    win = MainWindow()
    win.inventory = inv
    win.cart = CartController(db=db)
    win.refresh_reports()

    assert win.reports_sessions_label.text() == f"Current open session #{open_shift.id}"
    assert win.reports_item_count_label.text() == "1"
    assert win.reports_units_sold_label.text() == "1"
    assert win.reports_revenue_label.text() == "£4.00"
    assert _table_rows(win.reports_table) == [["Cake", "Snacks", "", "1", "£4.00"]]


def test_reports_tab_can_aggregate_selected_sessions(tmp_path):
    try:
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "reports_selected_sessions_ui.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    tea = inv.add_product("Tea", 2.00, category="Hot Drinks")
    cake = inv.add_product("Cake", 4.00, category="Snacks")

    first_cart = CartController(db=db)
    first_cart.add_item(tea)
    first_cart.checkout(payment_method="Cash")
    closed_shift, open_shift = db.close_current_shift()

    second_cart = CartController(db=db)
    second_cart.add_item(tea, quantity=2)
    second_cart.add_item(cake)
    second_cart.checkout(payment_method="Visa")

    win = MainWindow()
    win.inventory = inv
    win.cart = CartController(db=db)
    win.refresh_reports()
    _set_reports_shift_selection(win, [closed_shift.id, open_shift.id])

    rows_by_name = {row[0]: row for row in _table_rows(win.reports_table)}
    assert win.reports_sessions_label.text() == "2 selected sessions"
    assert win.reports_item_count_label.text() == "2"
    assert win.reports_units_sold_label.text() == "4"
    assert win.reports_revenue_label.text() == "£10.00"
    assert rows_by_name["Tea"] == ["Tea", "Hot Drinks", "", "3", "£6.00"]
    assert rows_by_name["Cake"] == ["Cake", "Snacks", "", "1", "£4.00"]


def test_reports_tab_can_filter_by_date_range_without_session_selection(tmp_path):
    try:
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "reports_date_range_ui.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    tea = inv.add_product("Tea", 2.00, category="Hot Drinks")
    cake = inv.add_product("Cake", 4.00, category="Snacks")

    first_cart = CartController(db=db)
    first_cart.add_item(tea)
    first_txn = first_cart.checkout(payment_method="Cash")
    db.update_transaction(
        Transaction(
            id=first_txn.id,
            payment_method=first_txn.payment_method,
            timestamp=datetime.datetime(2026, 3, 10, 9, 0, 0),
            items=first_txn.items,
        )
    )
    db.close_current_shift(closed_at=datetime.datetime(2026, 3, 10, 10, 0, 0))

    second_cart = CartController(db=db)
    second_cart.add_item(cake)
    second_txn = second_cart.checkout(payment_method="Visa")
    db.update_transaction(
        Transaction(
            id=second_txn.id,
            payment_method=second_txn.payment_method,
            timestamp=datetime.datetime(2026, 3, 11, 12, 30, 0),
            items=second_txn.items,
        )
    )

    win = MainWindow()
    win.inventory = inv
    win.cart = CartController(db=db)
    win.refresh_reports()

    _set_reports_shift_selection(win, [])
    win.reports_from_checkbox.setChecked(True)
    win.reports_from_datetime.setDateTime(
        QtCore.QDateTime(QtCore.QDate(2026, 3, 11), QtCore.QTime(0, 0))
    )
    win.reports_to_checkbox.setChecked(True)
    win.reports_to_datetime.setDateTime(
        QtCore.QDateTime(QtCore.QDate(2026, 3, 11), QtCore.QTime(23, 59))
    )
    win.refresh_reports(refresh_shift_filter=False)

    assert win.reports_sessions_label.text() == "All sessions in selected time range"
    assert win.reports_item_count_label.text() == "1"
    assert win.reports_units_sold_label.text() == "1"
    assert win.reports_revenue_label.text() == "£4.00"
    assert _table_rows(win.reports_table) == [["Cake", "Snacks", "", "1", "£4.00"]]


def test_checkout_still_succeeds_when_automatic_backup_fails(tmp_path, monkeypatch):
    try:
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "checkout_backup_warning.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    prod = inv.add_product("Coffee", 2.50, category="Hot Drinks")

    win = MainWindow()
    win.inventory = inv
    win.cart = CartController(db=db)
    win.choose_payment_method = lambda: "Cash"
    win.show_receipt_dialog = lambda *args, **kwargs: None

    warning_messages: list[str] = []
    monkeypatch.setattr(
        db.backups,
        "create_timestamped_backup",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("disk full")),
    )
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "warning",
        staticmethod(lambda *args, **kwargs: warning_messages.append(args[2])),
    )

    win.cart.add_item(prod)
    win.perform_checkout()

    assert win.bills_list.count() == 1
    assert db.list_transactions(limit=10)[0].payment_method == "Cash"
    assert any("Automatic checkout backup failed." in message for message in warning_messages)


def test_edit_bill_refreshes_history_details_and_reports(tmp_path, monkeypatch):
    try:
        from interface.till import bills_mixin as bills_module
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "edit_bill_ui.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    coffee = inv.add_product("Coffee", 2.50, category="Hot Drinks")
    cake = inv.add_product("Cake", 4.00, category="Snacks")

    cart = CartController(db=db)
    cart.add_item(coffee, quantity=2)
    cart.add_item(cake)
    txn = cart.checkout(payment_method="Cash")

    win = MainWindow()
    win.inventory = inv
    win.cart = CartController(db=db)
    win.check_pin = lambda: True
    win.refresh_bills()

    monkeypatch.setattr(
        bills_module,
        "prompt_edit_bill",
        lambda parent, transaction: Transaction(
            id=transaction.id,
            payment_method="Mastercard",
            timestamp=datetime.datetime(2026, 3, 10, 21, 5, 0),
            items=[
                TransactionItem(
                    product_id=coffee.id,
                    product_name="Mocha",
                    unit_price=4.50,
                    quantity=1,
                    category="Hot Drinks",
                    sub_category="",
                )
            ],
        ),
    )

    win.edit_selected_bill()

    assert "EDITED" in win.bills_list.item(0).text()
    assert "Mastercard" in win.bills_list.item(0).text()
    assert "£4.50" in win.bills_list.item(0).text()
    assert "10/03 21:05" in win.bills_list.item(0).text()
    assert win.bills_list.item(0).background().color().name() == "#5a4321"
    assert win.bills_list.item(0).toolTip().startswith("Edited bill at ")
    assert not win.bill_status_badge.isHidden()
    assert win.bill_status_badge.text().startswith("Edited at ")
    assert "mocha" in win.bill_detail.toPlainText().lower()
    assert "2026-03-10 21:05:00" in win.bill_detail.toPlainText()
    assert "total: £4.50" in win.bill_detail.toPlainText().lower()
    assert "saved edits" not in win.bill_detail.toPlainText().lower()
    assert not win.bill_audit_group.isHidden()
    assert "saved edits" in win.bill_audit_detail.toPlainText().lower()
    assert "payment: cash -> mastercard" in win.bill_audit_detail.toPlainText().lower()
    assert "removed: cake x1 @ £4.00 = £4.00".lower() in win.bill_audit_detail.toPlainText().lower()
    assert "changed (name, qty, price): coffee x2 @ £2.50 = £5.00 -> mocha x1 @ £4.50 = £4.50".lower() in win.bill_audit_detail.toPlainText().lower()
    detail_html = win.format_bill_audit_html(db.get_transaction(txn.id))
    assert "removed: cake x1 @ £4.00 = £4.00".lower() in detail_html.lower()
    assert "background-color: #6a2424" in detail_html.lower()
    assert win.bills_cash_label.text() == "£0.00"
    assert win.bills_card_label.text() == "£4.50"
    assert win.bills_mastercard_label.text() == "£4.50"
    assert win.reports_item_count_label.text() == "1"
    assert win.reports_units_sold_label.text() == "1"
    assert win.reports_revenue_label.text() == "£4.50"
    assert _table_rows(win.reports_table) == [["Mocha", "Hot Drinks", "", "1", "£4.50"]]

    report_text = win.format_shift_report_text(
        db.get_shift_summary(txn.shift_id),
        db.list_transactions(limit=200, shift_id=txn.shift_id),
    )
    assert "Mastercard: £4.50" in report_text
    assert "2026-03-10 21:05:00" in report_text
    assert "#1  2026-03-10 21:05:00  Mastercard  £4.50" in report_text
    assert "Mocha x1 @ £4.50 = £4.50" not in report_text


def test_edited_bill_remains_highlighted_after_reloading_history(tmp_path, monkeypatch):
    try:
        from interface.till import bills_mixin as bills_module
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "edit_bill_highlight.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    prod = inv.add_product("Tea", 2.00, category="Hot Drinks")

    cart = CartController(db=db)
    cart.add_item(prod)
    txn = cart.checkout(payment_method="Cash")

    win = MainWindow()
    win.inventory = inv
    win.cart = CartController(db=db)
    win.check_pin = lambda: True
    win.refresh_bills()

    monkeypatch.setattr(
        bills_module,
        "prompt_edit_bill",
        lambda parent, transaction: Transaction(
            id=transaction.id,
            payment_method="Cash",
            timestamp=transaction.timestamp,
            items=[
                TransactionItem(
                    product_id=prod.id,
                    product_name="Edited Tea",
                    unit_price=2.50,
                    quantity=1,
                    category="Hot Drinks",
                    sub_category="",
                )
            ],
        ),
    )

    win.edit_selected_bill()
    win.refresh_bills()

    item = win.bills_list.item(0)
    assert item is not None
    assert "EDITED" in item.text()
    assert item.data(QtCore.Qt.ItemDataRole.UserRole) == txn.id
    assert item.background().color().name() == "#5a4321"
    assert item.toolTip().startswith("Edited bill at ")
    assert not win.bill_audit_group.isHidden()
    assert "saved edits" in win.bill_audit_detail.toPlainText().lower()


def test_saved_edits_section_can_collapse_and_expand(tmp_path, monkeypatch):
    try:
        from interface.till import bills_mixin as bills_module
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "edit_bill_collapse.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    coffee = inv.add_product("Coffee", 2.50, category="Hot Drinks")
    cake = inv.add_product("Cake", 4.00, category="Snacks")

    cart = CartController(db=db)
    cart.add_item(coffee)
    cart.add_item(cake)
    txn = cart.checkout(payment_method="Cash")

    win = MainWindow()
    win.inventory = inv
    win.cart = CartController(db=db)
    win.check_pin = lambda: True
    win.refresh_bills()

    monkeypatch.setattr(
        bills_module,
        "prompt_edit_bill",
        lambda parent, transaction: Transaction(
            id=transaction.id,
            payment_method="Visa",
            timestamp=transaction.timestamp,
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
        ),
    )

    win.edit_selected_bill()

    assert not win.bill_audit_group.isHidden()
    assert not win.bill_audit_content.isHidden()
    assert win.bill_audit_toggle.arrowType() == QtCore.Qt.ArrowType.DownArrow

    win.bill_audit_toggle.click()

    assert win.bill_audit_content.isHidden()
    assert win.bill_audit_toggle.arrowType() == QtCore.Qt.ArrowType.RightArrow

    win.bill_audit_toggle.click()

    assert not win.bill_audit_content.isHidden()
    assert win.bill_audit_toggle.arrowType() == QtCore.Qt.ArrowType.DownArrow
    assert "removed: cake x1 @ £4.00 = £4.00".lower() in win.bill_audit_detail.toPlainText().lower()


def test_main_window_close_releases_assigned_database(tmp_path):
    try:
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "close_window.db"
    db = Database(path=db_file)

    win = MainWindow()
    win.inventory = InventoryController(db=db)
    win.cart = CartController(db=db)
    win.close()

    assert db.conn is None


def test_restore_backup_refreshes_bills_and_clears_cart(tmp_path, monkeypatch):
    try:
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "restore_backup_ui.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    prod = inv.add_product("Toast", 3.00, category="Snacks")

    first_cart = CartController(db=db)
    first_cart.add_item(prod)
    first_cart.checkout(payment_method="Cash")
    backup_path = db.backups.create_timestamped_backup()

    second_cart = CartController(db=db)
    second_cart.add_item(prod, quantity=2)
    second_cart.checkout(payment_method="Visa")

    win = MainWindow()
    win.inventory = inv
    win.cart = CartController(db=db)
    win.check_pin = lambda: True
    win.cart.add_item(prod)
    win.refresh_cart()
    win.refresh_bills()

    info_messages: list[str] = []
    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getItem",
        staticmethod(lambda *args, **kwargs: (win.build_backup_choice_label(backup_path), True)),
    )
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "question",
        staticmethod(lambda *args, **kwargs: QtWidgets.QMessageBox.StandardButton.Yes),
    )
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "information",
        staticmethod(lambda *args, **kwargs: info_messages.append(args[2])),
    )

    assert win.bills_list.count() == 2
    assert win.cart_list.count() == 1

    win.restore_data_backup()

    assert win.bills_list.count() == 1
    assert win.bills_count_label.text() == "1"
    assert "Cash" in win.bills_list.item(0).text()
    assert "Visa" not in win.bills_list.item(0).text()
    assert win.cart_list.count() == 0
    assert win.reports_item_count_label.text() == "1"
    assert win.reports_units_sold_label.text() == "1"
    assert win.reports_revenue_label.text() == "£3.00"
    assert _table_rows(win.reports_table) == [["Toast", "Snacks", "", "1", "£3.00"]]
    assert any("Safety backup saved as" in message for message in info_messages)


def test_close_day_keeps_bill_history_and_resets_shift_summary(tmp_path, monkeypatch):
    try:
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "close_day_ui.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    prod = inv.add_product("Toast", 3.00, category="Snacks")

    win = MainWindow()
    win.inventory = inv
    win.cart = CartController(db=db)
    win.choose_payment_method = lambda: "Amex"
    win.show_receipt_dialog = lambda *args, **kwargs: None
    win.check_pin = lambda: True
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "question",
        staticmethod(lambda *args, **kwargs: QtWidgets.QMessageBox.StandardButton.Yes),
    )
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "information",
        staticmethod(lambda *args, **kwargs: None),
    )
    reported_shifts = []
    win.show_shift_report_dialog = lambda shift_id, title=None: reported_shifts.append((shift_id, title))

    win.cart.add_item(prod)
    win.perform_checkout()

    before_close_shift = db.get_or_create_open_shift().id
    assert win.bills_list.count() == 1
    assert win.bills_count_label.text() == "1"

    win.close_current_day()

    after_close_shift = db.get_or_create_open_shift().id
    assert after_close_shift != before_close_shift
    assert reported_shifts == [
        (before_close_shift, f"End Of Day Report - Shift #{before_close_shift}")
    ]
    assert win.bills_list.count() == 0
    assert win.bills_count_label.text() == "0"
    assert win.bills_amex_label.text() == "£0.00"
    assert f"#{after_close_shift} (Open)" == win.bills_shift_label.text()
    assert win.reports_sessions_label.text() == f"Current open session #{after_close_shift}"
    assert win.reports_item_count_label.text() == "0"
    assert win.reports_units_sold_label.text() == "0"
    assert win.reports_revenue_label.text() == "£0.00"
    assert len(db.backups.list_backups()) == 2

    win.set_bills_shift_filter(before_close_shift)
    assert win.bills_list.count() == 1
    assert win.bills_amex_label.text() == "£3.00"
    _set_reports_shift_selection(win, [before_close_shift])
    assert _table_rows(win.reports_table) == [["Toast", "Snacks", "", "1", "£3.00"]]


def test_close_day_still_succeeds_when_automatic_backup_fails(tmp_path, monkeypatch):
    try:
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "close_day_backup_warning.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    prod = inv.add_product("Toast", 3.00, category="Snacks")

    win = MainWindow()
    win.inventory = inv
    win.cart = CartController(db=db)
    win.choose_payment_method = lambda: "Cash"
    win.show_receipt_dialog = lambda *args, **kwargs: None
    win.check_pin = lambda: True

    warning_messages: list[str] = []
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "question",
        staticmethod(lambda *args, **kwargs: QtWidgets.QMessageBox.StandardButton.Yes),
    )
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "information",
        staticmethod(lambda *args, **kwargs: None),
    )
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "warning",
        staticmethod(lambda *args, **kwargs: warning_messages.append(args[2])),
    )

    win.cart.add_item(prod)
    win.perform_checkout()
    monkeypatch.setattr(
        db.backups,
        "create_timestamped_backup",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("backup disk full")),
    )

    reported_shifts = []
    win.show_shift_report_dialog = lambda shift_id, title=None: reported_shifts.append((shift_id, title))
    before_close_shift = db.get_or_create_open_shift().id

    win.close_current_day()

    after_close_shift = db.get_or_create_open_shift().id
    assert after_close_shift != before_close_shift
    assert reported_shifts == [
        (before_close_shift, f"End Of Day Report - Shift #{before_close_shift}")
    ]
    assert any("Automatic close-day backup failed." in message for message in warning_messages)


def test_bills_can_filter_to_closed_shift(tmp_path, monkeypatch):
    try:
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "shift_filter_ui.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    first = inv.add_product("Tea", 2.00, category="Hot Drinks")
    second = inv.add_product("Cake", 4.00, category="Snacks")

    first_cart = CartController(db=db)
    first_cart.add_item(first)
    first_cart.checkout(payment_method="Cash")
    closed_shift, open_shift = db.close_current_shift()

    second_cart = CartController(db=db)
    second_cart.add_item(second)
    second_cart.checkout(payment_method="Mastercard")

    win = MainWindow()
    win.inventory = inv
    win.cart = CartController(db=db)
    win.refresh_bills()

    assert f"#{open_shift.id} (Open)" == win.bills_shift_label.text()
    assert win.bills_list.count() == 1
    assert "Cake".lower() in win.bill_detail.toPlainText().lower()
    assert "Mastercard" in win.bills_list.item(0).text()
    assert win.bills_mastercard_label.text() == "£4.00"

    win.set_bills_shift_filter(closed_shift.id)

    assert f"#{closed_shift.id} (Closed)" == win.bills_shift_label.text()
    assert win.bills_list.count() == 1
    assert "Tea".lower() in win.bill_detail.toPlainText().lower()
    assert win.bills_count_label.text() == "1"
    assert win.bills_mastercard_label.text() == "£0.00"


def test_end_of_day_report_uses_selected_shift_history(tmp_path):
    try:
        from interface.till.views import MainWindow
    except ImportError:
        pytest.skip("PyQt6 not available")

    db_file = tmp_path / "end_of_day_report.db"
    db = Database(path=db_file)
    inv = InventoryController(db=db)
    tea = inv.add_product("Tea", 2.00, category="Hot Drinks")
    cake = inv.add_product("Cake", 4.00, category="Snacks")

    first_cart = CartController(db=db)
    first_cart.add_item(tea)
    first_cash = first_cart.checkout(payment_method="Cash")
    first_cart.add_item(cake)
    first_visa = first_cart.checkout(payment_method="Visa")
    closed_shift, _ = db.close_current_shift()

    second_cart = CartController(db=db)
    second_cart.add_item(cake)
    second_cart.checkout(payment_method="Amex")

    win = MainWindow()
    win.inventory = inv
    win.cart = CartController(db=db)
    win.refresh_bills()
    win.set_bills_shift_filter(closed_shift.id)

    report_text = win.format_shift_report_text(
        db.get_shift_summary(closed_shift.id),
        db.list_transactions(limit=500, shift_id=closed_shift.id),
    )

    assert "End Of Day Report" in report_text
    assert f"Shift: #{closed_shift.id}" in report_text
    assert "Transactions: 2" in report_text
    assert "Cash: £2.00" in report_text
    assert "Card: £4.00" in report_text
    assert "Visa: £4.00" in report_text
    assert "Mastercard: £0.00" in report_text
    assert "Amex: £0.00" in report_text
    assert "Total: £6.00" in report_text
    assert "Payment Breakdown (Newest first)" in report_text
    visa_line = f"#{first_visa.id}  {first_visa.timestamp.strftime('%Y-%m-%d %H:%M:%S')}  Visa  £4.00"
    cash_line = f"#{first_cash.id}  {first_cash.timestamp.strftime('%Y-%m-%d %H:%M:%S')}  Cash  £2.00"
    assert visa_line in report_text
    assert cash_line in report_text
    payment_section = report_text.split("Payment Breakdown (Newest first)\n", 1)[1]
    assert payment_section.index(visa_line) < payment_section.index(cash_line)
    assert "Tea x1 @ £2.00 = £2.00" not in report_text
    assert "Cake x1 @ £4.00 = £4.00" not in report_text


@pytest.fixture(autouse=True)
def clear_db(tmp_path, monkeypatch):
    # ensure get_db returns new database each test
    from interface.till import db as dbmod
    dbmod._db_instance = None
    yield
