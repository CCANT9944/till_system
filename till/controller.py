"""Controller logic for till interface."""

from typing import List

from .db import get_db
from .models import CartItem, Product, Transaction, TransactionItem


class InventoryController:
    def __init__(self, db=None):
        self.db = db or get_db()

    def add_product(
        self,
        name: str,
        price: float,
        category: str = "",
        sub_category: str = "",
        barcode: str = "",
        color: str = "",
        font_size: int = 10,
        tile_order: int = 0,
        tile_row: int | None = None,
        tile_column: int | None = None,
    ) -> Product:
        prod = Product(
            name=name,
            price=price,
            category=category,
            sub_category=sub_category,
            barcode=barcode,
            color=color,
            font_size=font_size,
            tile_order=tile_order,
            tile_row=tile_row,
            tile_column=tile_column,
        )
        prod.id = self.db.add_product(prod)
        if not prod.tile_order:
            prod.tile_order = prod.id
        return prod

    def delete_product(self, product_id: int) -> None:
        self.db.delete_product(product_id)

    def update_product(self, product: Product) -> None:
        self.db.update_product(product)

    def list_products(self) -> List[Product]:
        return self.db.list_products()


class CartController:
    def __init__(self, db=None):
        self.db = db or get_db()
        self.items: List[CartItem] = []

    def add_item(self, product: Product, quantity: int = 1):
        for item in self.items:
            if item.product.id == product.id:
                item.quantity += quantity
                return item
        item = CartItem(product=product, quantity=quantity)
        self.items.append(item)
        return item

    def total(self) -> float:
        return sum(item.total_price for item in self.items)

    def clear(self):
        self.items.clear()

    def checkout(self, payment_method: str = "Cash") -> Transaction:
        txn = Transaction(
            items=[
                TransactionItem(
                    product_id=item.product.id,
                    product_name=item.product.name,
                    unit_price=item.product.price,
                    quantity=item.quantity,
                    category=item.product.category,
                    sub_category=item.product.sub_category,
                )
                for item in self.items
            ],
            total=self.total(),
            payment_method=payment_method,
        )
        txn.id = self.db.record_transaction(txn)
        self.clear()
        return txn
