"""Exact decimal money helpers. Floats are never used for money."""
from decimal import Decimal, ROUND_HALF_EVEN, InvalidOperation

CENT = Decimal("0.01")
ZERO = Decimal("0")


def D(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        # Route through repr to avoid binary float artifacts.
        value = repr(value)
    try:
        return Decimal(str(value).strip().replace(",", "").replace("$", ""))
    except (InvalidOperation, AttributeError) as exc:
        raise ValueError(f"not a decimal amount: {value!r}") from exc


def cents(value) -> Decimal:
    return D(value).quantize(CENT, rounding=ROUND_HALF_EVEN)


def fmt(value) -> str:
    return f"${cents(value):,.2f}"
