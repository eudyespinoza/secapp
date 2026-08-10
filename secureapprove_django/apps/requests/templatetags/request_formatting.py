from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django import template


register = template.Library()


@register.filter
def format_amount(value):
    """Render money with dot thousands and exactly two comma decimals."""
    if value in (None, ""):
        return ""

    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return value

    if not amount.is_finite():
        return value

    # Avoid displaying negative zero after rounding very small values.
    if amount == 0:
        amount = abs(amount)

    grouped = f"{amount:,.2f}"
    return grouped.translate(str.maketrans({",": ".", ".": ","}))
