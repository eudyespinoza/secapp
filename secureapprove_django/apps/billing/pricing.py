# ==================================================
# SecureApprove Django - Billing Pricing Helpers
# ==================================================

from decimal import Decimal


def get_price_per_user(seats: int) -> Decimal:
    """
    Return price per user (USD) based on total users.

    Rules:
      - 2–6 users  -> 60 USD/user
      - 7–12 users -> 55 USD/user
      - >12 users  -> 50 USD/user

    If seats < 2, we still charge using the lowest tier (60).
    """
    if seats is None:
        seats = 0

    try:
        seats_int = int(seats)
    except (TypeError, ValueError):
        seats_int = 0

    if seats_int <= 0:
        seats_int = 1

    if seats_int <= 6:
        return Decimal("60.00")
    if seats_int <= 12:
        return Decimal("55.00")
    return Decimal("50.00")


__all__ = ["get_price_per_user"]

