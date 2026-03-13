"""Shared helpers for rendering saved bill revision history."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from .models import Transaction, TransactionItem, TransactionRevision

StateLike = Transaction | TransactionRevision


@dataclass(frozen=True)
class BillAuditEntry:
    edit_number: int
    saved_at: datetime.datetime | None
    before_state: StateLike
    after_state: StateLike
    lines: list[str]


def format_bill_item_summary(item: TransactionItem, *, currency_symbol: str = "£") -> str:
    return (
        f"{item.product_name} x{item.quantity} @ {currency_symbol}{item.unit_price:.2f} = "
        f"{currency_symbol}{item.line_total:.2f}"
    )


def transaction_item_signature(item: TransactionItem) -> tuple[object, ...]:
    return (
        item.product_id,
        item.product_name.strip().casefold(),
        round(float(item.unit_price or 0.0), 2),
        int(item.quantity or 0),
        item.category.strip().casefold(),
        item.sub_category.strip().casefold(),
    )


def pair_bill_items(
    before_items: list[TransactionItem],
    after_items: list[TransactionItem],
) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    unmatched_before = list(range(len(before_items)))
    unmatched_after = list(range(len(after_items)))
    pairs: list[tuple[int, int]] = []

    def match_items(matcher) -> None:
        matched_before: list[int] = []
        for before_index in list(unmatched_before):
            candidates = [
                after_index
                for after_index in unmatched_after
                if matcher(before_items[before_index], after_items[after_index])
            ]
            if not candidates:
                continue
            after_index = min(candidates, key=lambda index: abs(index - before_index))
            unmatched_after.remove(after_index)
            matched_before.append(before_index)
            pairs.append((before_index, after_index))
        for before_index in matched_before:
            unmatched_before.remove(before_index)

    match_items(lambda before, after: transaction_item_signature(before) == transaction_item_signature(after))
    match_items(
        lambda before, after: (
            before.product_id is not None
            and after.product_id is not None
            and before.product_id == after.product_id
        )
    )
    match_items(lambda before, after: before.product_name.strip().casefold() == after.product_name.strip().casefold())

    pairs.sort(key=lambda pair: pair[1])
    return pairs, unmatched_before, unmatched_after


def describe_bill_change(
    before_state: StateLike,
    after_state: StateLike,
    *,
    currency_symbol: str = "£",
) -> list[str]:
    lines: list[str] = []
    if before_state.payment_method != after_state.payment_method:
        lines.append(f"Payment: {before_state.payment_method} -> {after_state.payment_method}")
    if before_state.timestamp != after_state.timestamp:
        lines.append(
            "Date: "
            f"{before_state.timestamp.strftime('%Y-%m-%d %H:%M:%S')} -> "
            f"{after_state.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    pairs, unmatched_before, unmatched_after = pair_bill_items(before_state.items, after_state.items)
    for before_index, after_index in pairs:
        before_item = before_state.items[before_index]
        after_item = after_state.items[after_index]
        if transaction_item_signature(before_item) == transaction_item_signature(after_item):
            continue
        changed_fields: list[str] = []
        if before_item.product_name != after_item.product_name:
            changed_fields.append("name")
        if before_item.quantity != after_item.quantity:
            changed_fields.append("qty")
        if round(before_item.unit_price, 2) != round(after_item.unit_price, 2):
            changed_fields.append("price")
        change_label = ", ".join(changed_fields) if changed_fields else "details"
        lines.append(
            f"Changed ({change_label}): "
            f"{format_bill_item_summary(before_item, currency_symbol=currency_symbol)} -> "
            f"{format_bill_item_summary(after_item, currency_symbol=currency_symbol)}"
        )

    for before_index in unmatched_before:
        lines.append(
            f"Removed: {format_bill_item_summary(before_state.items[before_index], currency_symbol=currency_symbol)}"
        )
    for after_index in unmatched_after:
        lines.append(
            f"Added: {format_bill_item_summary(after_state.items[after_index], currency_symbol=currency_symbol)}"
        )

    if round(before_state.total, 2) != round(after_state.total, 2):
        lines.append(f"Total: {currency_symbol}{before_state.total:.2f} -> {currency_symbol}{after_state.total:.2f}")
    return lines or ["No saved differences detected."]


def build_bill_audit_entries(
    transaction: Transaction,
    revisions: list[TransactionRevision],
    *,
    currency_symbol: str = "£",
) -> list[BillAuditEntry]:
    comparisons: list[tuple[StateLike, StateLike]] = []
    for index, revision in enumerate(revisions):
        next_state: StateLike = revisions[index + 1] if index + 1 < len(revisions) else transaction
        comparisons.append((revision, next_state))

    total_edits = len(comparisons)
    entries: list[BillAuditEntry] = []
    for offset, (before_state, after_state) in enumerate(reversed(comparisons), start=1):
        edit_number = total_edits - offset + 1
        saved_at = after_state.edited_at
        if saved_at is None and isinstance(after_state, TransactionRevision):
            saved_at = after_state.captured_at
        entries.append(
            BillAuditEntry(
                edit_number=edit_number,
                saved_at=saved_at,
                before_state=before_state,
                after_state=after_state,
                lines=describe_bill_change(before_state, after_state, currency_symbol=currency_symbol),
            )
        )
    return entries