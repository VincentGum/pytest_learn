import logging
import os
from typing import List

from .models import Item, User

logger = logging.getLogger("app.pricing")


def membership_discount(tier: str) -> float:
    if tier == "vip":
        return 0.10
    return 0.0


def coupon_discount() -> float:
    code = os.environ.get("COUPON_CODE", "")
    if code == "SAVE5":
        return 0.05
    return 0.0


def calculate_subtotal(items: List[Item]) -> float:
    subtotal = sum(i.price for i in items)
    logger.info("subtotal=%s", subtotal)
    return subtotal


def calculate_total(items: List[Item], user: User, region: str = "CN") -> float:
    subtotal = calculate_subtotal(items)
    discount = membership_discount(user.tier) + coupon_discount()
    discounted = subtotal * (1 - discount)
    taxed = apply_tax(discounted, region)
    logger.debug("total computed: %s", taxed)
    return round(taxed, 2)


def apply_tax(amount: float, region: str) -> float:
    tax_rate = 0.0
    if region == "CN":
        tax_rate = 0.13
    elif region == "US":
        tax_rate = 0.07
    else:
        tax_rate = 0.10
    return amount * (1 + tax_rate)
