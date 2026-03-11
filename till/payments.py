"""Payment method helpers for till checkout and reporting."""

CHECKOUT_PAYMENT_METHODS = (
    "Cash",
    "Visa",
    "Mastercard",
    "Amex",
)

CARD_SCHEME_PAYMENT_METHODS = (
    "Visa",
    "Mastercard",
    "Amex",
)

# Keep legacy "Card" rows grouped with the newer named card schemes.
CARD_PAYMENT_METHODS = (
    "Card",
    "Visa",
    "Mastercard",
    "Amex",
)

CARD_PAYMENT_METHOD_SQL = ", ".join(
    f"'{payment_method.lower()}'" for payment_method in CARD_PAYMENT_METHODS
)


def get_payment_method_total_sql(payment_method: str) -> str:
    return (
        "COALESCE(SUM(CASE "
        f"WHEN lower(payment_method) = '{payment_method.lower()}' THEN total "
        "ELSE 0 END), 0)"
    )