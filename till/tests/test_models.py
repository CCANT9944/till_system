import pytest

from interface.till.models import Product, CartItem, Transaction


def test_product_dataclass():
    p = Product(id=1, name="Test", price=9.99)
    assert p.id == 1
    assert p.name == "Test"
    assert p.price == 9.99


def test_cart_item_total():
    p = Product(id=1, name="Test", price=2.50)
    item = CartItem(product=p, quantity=3)
    assert item.total_price == 7.50


def test_transaction_default():
    t = Transaction()
    assert t.total == 0.0
    assert isinstance(t.timestamp, type(t.timestamp))
