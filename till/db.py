"""Database layer for till system using SQLite."""

from contextlib import contextmanager
import datetime
import sqlite3
from pathlib import Path
from typing import List

from .backup_service import BackupService
from .models import Product, Shift, Transaction, TransactionItem
from .payments import CARD_PAYMENT_METHOD_SQL, get_payment_method_total_sql

DB_FILE = Path(__file__).parent / "till.db"


class Database:
    def __init__(self, path: Path = None):
        self.path = path or DB_FILE
        self.conn: sqlite3.Connection | None = None
        self.backups = BackupService(
            self.path,
            self._require_connection,
            self.close,
            self._connect,
        )
        self._connect()

    def _connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path), timeout=5.0)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA busy_timeout = 5000")
        self._init_schema()

    def _require_connection(self) -> sqlite3.Connection:
        if self.conn is None:
            raise RuntimeError("Database connection is closed.")
        return self.conn

    @contextmanager
    def _atomic_write(self):
        conn = self._require_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()

    def close(self) -> None:
        if self.conn is None:
            return
        try:
            self.conn.rollback()
        except sqlite3.Error:
            pass
        self.conn.close()
        self.conn = None

    def _init_schema(self):
        c = self._require_connection().cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                opened_at TEXT NOT NULL,
                closed_at TEXT,
                transaction_count INTEGER NOT NULL DEFAULT 0,
                total REAL NOT NULL DEFAULT 0,
                cash_total REAL NOT NULL DEFAULT 0,
                card_total REAL NOT NULL DEFAULT 0
            )
            """
        )
        # create table with category column; older databases will be migrated below
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                barcode TEXT,
                category TEXT,
                sub_category TEXT,
                color TEXT,
                font_size INTEGER DEFAULT 10,
                tile_order INTEGER DEFAULT 0,
                tile_row INTEGER,
                tile_column INTEGER
            )
            """
        )
        # ensure category and sub_category columns exist (in case we added them later)
        c.execute("PRAGMA table_info(products)")
        cols = [row[1] for row in c.fetchall()]
        if "category" not in cols:
            c.execute("ALTER TABLE products ADD COLUMN category TEXT")
        if "sub_category" not in cols:
            c.execute("ALTER TABLE products ADD COLUMN sub_category TEXT")
        if "color" not in cols:
            c.execute("ALTER TABLE products ADD COLUMN color TEXT")
        if "font_size" not in cols:
            c.execute("ALTER TABLE products ADD COLUMN font_size INTEGER DEFAULT 10")
        if "tile_order" not in cols:
            c.execute("ALTER TABLE products ADD COLUMN tile_order INTEGER DEFAULT 0")
        if "tile_row" not in cols:
            c.execute("ALTER TABLE products ADD COLUMN tile_row INTEGER")
        if "tile_column" not in cols:
            c.execute("ALTER TABLE products ADD COLUMN tile_column INTEGER")
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total REAL NOT NULL,
                timestamp TEXT NOT NULL,
                payment_method TEXT NOT NULL DEFAULT 'Cash',
                edited_at TEXT,
                shift_id INTEGER,
                FOREIGN KEY(shift_id) REFERENCES shifts(id)
            )
            """
        )
        c.execute("PRAGMA table_info(transactions)")
        transaction_cols = [row[1] for row in c.fetchall()]
        if "payment_method" not in transaction_cols:
            c.execute("ALTER TABLE transactions ADD COLUMN payment_method TEXT NOT NULL DEFAULT 'Cash'")
        if "edited_at" not in transaction_cols:
            c.execute("ALTER TABLE transactions ADD COLUMN edited_at TEXT")
        if "shift_id" not in transaction_cols:
            c.execute("ALTER TABLE transactions ADD COLUMN shift_id INTEGER")

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS transaction_items (
                transaction_id INTEGER,
                product_id INTEGER,
                quantity INTEGER,
                product_name TEXT,
                unit_price REAL,
                category TEXT,
                sub_category TEXT,
                FOREIGN KEY(transaction_id) REFERENCES transactions(id),
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
            """
        )
        c.execute("PRAGMA table_info(transaction_items)")
        transaction_item_cols = [row[1] for row in c.fetchall()]
        if "product_name" not in transaction_item_cols:
            c.execute("ALTER TABLE transaction_items ADD COLUMN product_name TEXT")
        if "unit_price" not in transaction_item_cols:
            c.execute("ALTER TABLE transaction_items ADD COLUMN unit_price REAL")
        if "category" not in transaction_item_cols:
            c.execute("ALTER TABLE transaction_items ADD COLUMN category TEXT")
        if "sub_category" not in transaction_item_cols:
            c.execute("ALTER TABLE transaction_items ADD COLUMN sub_category TEXT")
        self.conn.commit()
        self._migrate_legacy_transactions_to_shifts()
        self.get_or_create_open_shift()

    def _migrate_legacy_transactions_to_shifts(self) -> None:
        c = self.conn.cursor()
        c.execute(
             f"""
            SELECT substr(timestamp, 1, 10) AS txn_day,
                   MIN(timestamp),
                   MAX(timestamp),
                   COUNT(*),
                   COALESCE(SUM(total), 0),
                   COALESCE(SUM(CASE WHEN lower(payment_method) = 'cash' THEN total ELSE 0 END), 0),
                 COALESCE(SUM(CASE WHEN lower(payment_method) IN ({CARD_PAYMENT_METHOD_SQL}) THEN total ELSE 0 END), 0)
            FROM transactions
            WHERE shift_id IS NULL
            GROUP BY substr(timestamp, 1, 10)
            ORDER BY txn_day
             """
        )
        day_groups = c.fetchall()
        if not day_groups:
            return

        for _txn_day, min_timestamp, max_timestamp, count, total, cash_total, card_total in day_groups:
            c.execute(
                """
                INSERT INTO shifts (opened_at, closed_at, transaction_count, total, cash_total, card_total)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (min_timestamp, max_timestamp, count, total, cash_total, card_total),
            )
            shift_id = c.lastrowid
            c.execute(
                """
                UPDATE transactions
                SET shift_id = ?
                WHERE shift_id IS NULL AND substr(timestamp, 1, 10) = substr(?, 1, 10)
                """,
                (shift_id, min_timestamp),
            )
        self.conn.commit()

    def _shift_from_row(self, row) -> Shift:
        return Shift(
            id=row[0],
            opened_at=datetime.datetime.fromisoformat(row[1]),
            closed_at=datetime.datetime.fromisoformat(row[2]) if row[2] else None,
            transaction_count=int(row[3] or 0),
            total=float(row[4] or 0.0),
            cash_total=float(row[5] or 0.0),
            card_total=float(row[6] or 0.0),
        )

    def _create_shift(
        self,
        opened_at: datetime.datetime | None = None,
        *,
        commit: bool = True,
    ) -> Shift:
        shift_opened_at = opened_at or datetime.datetime.now()
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO shifts (opened_at) VALUES (?)",
            (shift_opened_at.isoformat(),),
        )
        if commit:
            self.conn.commit()
        return self.get_shift(c.lastrowid)

    def get_shift(self, shift_id: int) -> Shift | None:
        c = self.conn.cursor()
        c.execute(
            "SELECT id, opened_at, closed_at, transaction_count, total, cash_total, card_total FROM shifts WHERE id = ?",
            (shift_id,),
        )
        row = c.fetchone()
        if row is None:
            return None
        return self._shift_from_row(row)

    def get_or_create_open_shift(self, *, commit: bool = True) -> Shift:
        c = self.conn.cursor()
        c.execute(
            """
            SELECT id, opened_at, closed_at, transaction_count, total, cash_total, card_total
            FROM shifts
            WHERE closed_at IS NULL
            ORDER BY id DESC
            LIMIT 1
            """,
        )
        row = c.fetchone()
        if row is not None:
            return self._shift_from_row(row)
        return self._create_shift(commit=commit)

    def list_shifts(self, limit: int | None = None) -> List[Shift]:
        c = self.conn.cursor()
        query = "SELECT id, opened_at, closed_at, transaction_count, total, cash_total, card_total FROM shifts ORDER BY id DESC"
        params: tuple[object, ...] = ()
        if limit is not None:
            query += " LIMIT ?"
            params = (limit,)
        c.execute(query, params)
        return [self._shift_from_row(row) for row in c.fetchall()]

    def _build_payment_summary(self, row, *, shift_id: int, shift: Shift | None) -> dict[str, object]:
        return {
            "shift_id": shift_id,
            "opened_at": shift.opened_at if shift is not None else None,
            "closed_at": shift.closed_at if shift is not None else None,
            "is_open": shift.is_open if shift is not None else False,
            "count": int(row[0] or 0),
            "total": float(row[1] or 0.0),
            "cash_total": float(row[2] or 0.0),
            "card_total": float(row[3] or 0.0),
            "visa_total": float(row[4] or 0.0),
            "mastercard_total": float(row[5] or 0.0),
            "amex_total": float(row[6] or 0.0),
        }

    def get_shift_summary(self, shift_id: int) -> dict[str, object]:
        shift = self.get_shift(shift_id)
        if shift is None:
            return self._build_payment_summary(
                (0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
                shift_id=shift_id,
                shift=None,
            )

        c = self.conn.cursor()
        c.execute(
            f"""
            SELECT
                COUNT(*),
                COALESCE(SUM(total), 0),
                COALESCE(SUM(CASE WHEN lower(payment_method) = 'cash' THEN total ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN lower(payment_method) IN ({CARD_PAYMENT_METHOD_SQL}) THEN total ELSE 0 END), 0),
                {get_payment_method_total_sql('Visa')},
                {get_payment_method_total_sql('Mastercard')},
                {get_payment_method_total_sql('Amex')}
            FROM transactions
            WHERE shift_id = ?
            """,
            (shift_id,),
        )
        row = c.fetchone() or (0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        return self._build_payment_summary(row, shift_id=shift.id, shift=shift)

    def get_open_shift_summary(self) -> dict[str, object]:
        shift = self.get_or_create_open_shift()
        return self.get_shift_summary(shift.id)

    def close_current_shift(
        self,
        closed_at: datetime.datetime | None = None,
    ) -> tuple[Shift, Shift]:
        with self._atomic_write():
            current_shift = self.get_or_create_open_shift(commit=False)
            close_time = closed_at or datetime.datetime.now()
            summary = self.get_shift_summary(current_shift.id)

            c = self.conn.cursor()
            c.execute(
                """
                UPDATE shifts
                SET closed_at = ?,
                    transaction_count = ?,
                    total = ?,
                    cash_total = ?,
                    card_total = ?
                WHERE id = ?
                """,
                (
                    close_time.isoformat(),
                    summary["count"],
                    summary["total"],
                    summary["cash_total"],
                    summary["card_total"],
                    current_shift.id,
                ),
            )

            closed_shift = self.get_shift(current_shift.id)
            new_shift = self._create_shift(opened_at=close_time, commit=False)
        return closed_shift, new_shift

    def add_product(self, product: Product) -> int:
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO products (name, price, barcode, category, sub_category, color, font_size, tile_order, tile_row, tile_column) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                product.name,
                product.price,
                product.barcode,
                product.category,
                product.sub_category,
                product.color,
                product.font_size,
                product.tile_order,
                product.tile_row,
                product.tile_column,
            ),
        )
        self.conn.commit()
        product_id = c.lastrowid
        if not product.tile_order:
            c.execute("UPDATE products SET tile_order = ? WHERE id = ?", (product_id, product_id))
            self.conn.commit()
        return product_id

    def list_products(self) -> List[Product]:
        c = self.conn.cursor()
        c.execute(
            "SELECT id, name, price, barcode, category, sub_category, color, font_size, tile_order, tile_row, tile_column FROM products"
        )
        rows = c.fetchall()
        return [
            Product(
                id=r[0],
                name=r[1],
                price=r[2],
                barcode=r[3],
                category=r[4],
                sub_category=r[5],
                color=r[6] or "",
                font_size=r[7] or 10,
                tile_order=r[8] or 0,
                tile_row=r[9],
                tile_column=r[10],
            )
            for r in rows
        ]

    def delete_product(self, product_id: int) -> None:
        c = self.conn.cursor()
        c.execute("DELETE FROM products WHERE id = ?", (product_id,))
        self.conn.commit()

    def update_product(self, product: Product) -> None:
        c = self.conn.cursor()
        c.execute(
            "UPDATE products SET name=?, price=?, barcode=?, category=?, sub_category=?, color=?, font_size=?, tile_order=?, tile_row=?, tile_column=? WHERE id=?",
            (
                product.name,
                product.price,
                product.barcode,
                product.category,
                product.sub_category,
                product.color,
                product.font_size,
                product.tile_order,
                product.tile_row,
                product.tile_column,
                product.id,
            ),
        )
        self.conn.commit()

    def _sync_shift_totals(self, shift_id: int, *, commit: bool = True) -> None:
        shift = self.get_shift(shift_id)
        if shift is None:
            return
        summary = self.get_shift_summary(shift_id)
        c = self.conn.cursor()
        c.execute(
            """
            UPDATE shifts
            SET transaction_count = ?,
                total = ?,
                cash_total = ?,
                card_total = ?
            WHERE id = ?
            """,
            (
                summary["count"],
                summary["total"],
                summary["cash_total"],
                summary["card_total"],
                shift_id,
            ),
        )
        if commit:
            self.conn.commit()

    def _validate_transaction_items(self, items: list[TransactionItem]) -> list[TransactionItem]:
        if not items:
            raise ValueError("A bill must contain at least one item.")

        cleaned_items: list[TransactionItem] = []
        for item in items:
            name = item.product_name.strip()
            if not name:
                raise ValueError("Each bill item needs a name.")
            if item.quantity <= 0:
                raise ValueError("Each bill item needs a quantity above zero.")
            if item.unit_price is None or item.unit_price < 0:
                raise ValueError("Each bill item needs a valid unit price.")
            cleaned_items.append(
                TransactionItem(
                    product_id=item.product_id,
                    product_name=name,
                    unit_price=float(item.unit_price),
                    quantity=int(item.quantity),
                    category=item.category,
                    sub_category=item.sub_category,
                )
            )
        return cleaned_items

    def record_transaction(self, transaction: Transaction) -> int:
        if not transaction.payment_method:
            raise ValueError("Payment method is required.")
        cleaned_items = self._validate_transaction_items(transaction.items)
        total = sum(item.line_total for item in cleaned_items)

        with self._atomic_write():
            shift = self.get_or_create_open_shift(commit=False)
            c = self.conn.cursor()
            c.execute(
                "INSERT INTO transactions (total, timestamp, payment_method, edited_at, shift_id) VALUES (?, ?, ?, ?, ?)",
                (total, transaction.timestamp.isoformat(), transaction.payment_method, None, shift.id),
            )
            tid = c.lastrowid
            for item in cleaned_items:
                c.execute(
                    """
                    INSERT INTO transaction_items (
                        transaction_id,
                        product_id,
                        quantity,
                        product_name,
                        unit_price,
                        category,
                        sub_category
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tid,
                        item.product_id,
                        item.quantity,
                        item.product_name,
                        item.unit_price,
                        item.category,
                        item.sub_category,
                    ),
                )
            self._sync_shift_totals(shift.id, commit=False)

        transaction.items = cleaned_items
        transaction.total = total
        transaction.shift_id = shift.id
        transaction.edited_at = None
        return tid

    def update_transaction(self, transaction: Transaction) -> None:
        if transaction.id is None:
            raise ValueError("Transaction ID is required.")

        current_transaction = self.get_transaction(transaction.id)
        if current_transaction is None:
            raise ValueError("Transaction not found.")
        if not transaction.payment_method:
            raise ValueError("Payment method is required.")

        updated_timestamp = transaction.timestamp or current_transaction.timestamp
        edited_at = datetime.datetime.now()
        cleaned_items = self._validate_transaction_items(transaction.items)
        total = sum(item.line_total for item in cleaned_items)

        with self._atomic_write():
            c = self.conn.cursor()
            c.execute(
                "UPDATE transactions SET total = ?, payment_method = ?, timestamp = ?, edited_at = ? WHERE id = ?",
                (total, transaction.payment_method, updated_timestamp.isoformat(), edited_at.isoformat(), transaction.id),
            )
            c.execute("DELETE FROM transaction_items WHERE transaction_id = ?", (transaction.id,))
            for item in cleaned_items:
                c.execute(
                    """
                    INSERT INTO transaction_items (
                        transaction_id,
                        product_id,
                        quantity,
                        product_name,
                        unit_price,
                        category,
                        sub_category
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        transaction.id,
                        item.product_id,
                        item.quantity,
                        item.product_name,
                        item.unit_price,
                        item.category,
                        item.sub_category,
                    ),
                )
            if current_transaction.shift_id is not None:
                self._sync_shift_totals(current_transaction.shift_id, commit=False)

        transaction.items = cleaned_items
        transaction.total = total
        transaction.shift_id = current_transaction.shift_id
        transaction.timestamp = updated_timestamp
        transaction.edited_at = edited_at

    def get_transaction(self, transaction_id: int) -> Transaction | None:
        c = self.conn.cursor()
        c.execute(
            "SELECT id, total, timestamp, payment_method, edited_at, shift_id FROM transactions WHERE id = ?",
            (transaction_id,),
        )
        row = c.fetchone()
        if row is None:
            return None
        return Transaction(
            id=row[0],
            items=self.get_transaction_items(row[0]),
            total=row[1],
            payment_method=row[3] or "Cash",
            shift_id=row[5],
            timestamp=datetime.datetime.fromisoformat(row[2]),
            edited_at=datetime.datetime.fromisoformat(row[4]) if row[4] else None,
        )

    def get_transaction_items(self, transaction_id: int) -> List[TransactionItem]:
        c = self.conn.cursor()
        c.execute(
            """
            SELECT product_id, quantity, product_name, unit_price, category, sub_category
            FROM transaction_items
            WHERE transaction_id = ?
            ORDER BY rowid ASC
            """,
            (transaction_id,),
        )
        rows = c.fetchall()
        items: List[TransactionItem] = []
        for row in rows:
            product_id, quantity, product_name, unit_price, category, sub_category = row
            item_name = product_name or ""
            item_price = unit_price
            if (not item_name or item_price is None) and product_id is not None:
                product = next((value for value in self.list_products() if value.id == product_id), None)
                if product is not None:
                    if not item_name:
                        item_name = product.name
                    if item_price is None:
                        item_price = product.price
                    if not category:
                        category = product.category
                    if not sub_category:
                        sub_category = product.sub_category
            items.append(
                TransactionItem(
                    product_id=product_id,
                    product_name=item_name,
                    unit_price=item_price or 0.0,
                    quantity=quantity or 0,
                    category=category or "",
                    sub_category=sub_category or "",
                )
            )
        return items

    def list_transactions(
        self,
        limit: int | None = None,
        shift_id: int | None = None,
    ) -> List[Transaction]:
        c = self.conn.cursor()
        query = "SELECT id, total, timestamp, payment_method, edited_at, shift_id FROM transactions"
        params: tuple[object, ...] = ()
        if shift_id is not None:
            query += " WHERE shift_id = ?"
            params = (shift_id,)
        query += " ORDER BY timestamp DESC, id DESC"
        if limit is not None:
            query += " LIMIT ?"
            params = (*params, limit)
        c.execute(query, params)
        rows = c.fetchall()
        return [
            Transaction(
                id=row[0],
                items=self.get_transaction_items(row[0]),
                total=row[1],
                payment_method=row[3] or "Cash",
                shift_id=row[5],
                timestamp=datetime.datetime.fromisoformat(row[2]),
                edited_at=datetime.datetime.fromisoformat(row[4]) if row[4] else None,
            )
            for row in rows
        ]

    def get_daily_summary(self, day: datetime.date | None = None) -> dict[str, float | int]:
        report_day = day or datetime.date.today()
        day_key = report_day.isoformat()
        c = self.conn.cursor()
        c.execute(
            f"""
            SELECT
                COUNT(*),
                COALESCE(SUM(total), 0),
                COALESCE(SUM(CASE WHEN lower(payment_method) = 'cash' THEN total ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN lower(payment_method) IN ({CARD_PAYMENT_METHOD_SQL}) THEN total ELSE 0 END), 0),
                {get_payment_method_total_sql('Visa')},
                {get_payment_method_total_sql('Mastercard')},
                {get_payment_method_total_sql('Amex')}
            FROM transactions
            WHERE substr(timestamp, 1, 10) = ?
            """,
            (day_key,),
        )
        row = c.fetchone() or (0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        return {
            "date": day_key,
            "count": int(row[0] or 0),
            "total": float(row[1] or 0.0),
            "cash_total": float(row[2] or 0.0),
            "card_total": float(row[3] or 0.0),
            "visa_total": float(row[4] or 0.0),
            "mastercard_total": float(row[5] or 0.0),
            "amex_total": float(row[6] or 0.0),
        }


# convenience global
_db_instance: Database = None

def get_db() -> Database:
    global _db_instance
    if _db_instance is None or _db_instance.conn is None:
        _db_instance = Database()
    return _db_instance


def close_db() -> None:
    global _db_instance
    if _db_instance is not None:
        _db_instance.close()
        _db_instance = None
