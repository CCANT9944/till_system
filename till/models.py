"""Data models for till system."""

import datetime
from dataclasses import dataclass, field
from typing import List

@dataclass
class Product:
    id: int = None
    name: str = ""
    price: float = 0.0
    barcode: str = ""  # optional
    category: str = ""  # e.g. beer, spirits, hot drinks, cocktails, wines
    sub_category: str = ""  # e.g. Draught or Bottled for beer
    color: str = ""  # CSS color string for button background
    font_size: int = 10  # font size for the product tile button
    tile_order: int = 0  # order of the product inside the product grid
    tile_row: int | None = None  # explicit row inside the product grid
    tile_column: int | None = None  # explicit column inside the product grid

@dataclass
class CartItem:
    product: Product
    quantity: int = 1

    @property
    def total_price(self) -> float:
        return self.product.price * self.quantity


@dataclass
class TransactionItem:
    product_id: int | None = None
    product_name: str = ""
    unit_price: float = 0.0
    quantity: int = 1
    category: str = ""
    sub_category: str = ""

    @property
    def line_total(self) -> float:
        return self.unit_price * self.quantity


@dataclass
class Transaction:
    id: int = None
    items: List[TransactionItem] = field(default_factory=list)
    total: float = 0.0
    payment_method: str = "Cash"
    shift_id: int | None = None
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)
    edited_at: datetime.datetime | None = None


@dataclass
class TransactionRevision:
    id: int | None = None
    transaction_id: int | None = None
    items: List[TransactionItem] = field(default_factory=list)
    total: float = 0.0
    payment_method: str = "Cash"
    shift_id: int | None = None
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)
    edited_at: datetime.datetime | None = None
    captured_at: datetime.datetime = field(default_factory=datetime.datetime.now)


@dataclass
class Shift:
    id: int | None = None
    opened_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    closed_at: datetime.datetime | None = None
    transaction_count: int = 0
    total: float = 0.0
    cash_total: float = 0.0
    card_total: float = 0.0

    @property
    def is_open(self) -> bool:
        return self.closed_at is None


@dataclass
class ItemSalesSummary:
    product_name: str = ""
    category: str = ""
    sub_category: str = ""
    quantity_sold: int = 0
    revenue: float = 0.0
    transaction_count: int = 0
