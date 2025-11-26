import json
import time
from typing import List

from .models import Cart, Item, Order, User
from .pricing import calculate_total


def add_items(cart: Cart, items: List[Item]) -> Cart:
    for i in items:
        cart.add(i)
    return cart


def checkout(cart: Cart, user: User, region: str = "CN") -> Order:
    amount = calculate_total(cart.items, user, region)
    order = Order(user=user, items=list(cart.items), amount=amount)
    order.meta["ts"] = str(int(time.time()))
    order.meta["region"] = region
    return order


def print_receipt(order: Order) -> str:
    payload = {
        "user": order.user.id,
        "amount": order.amount,
        "count": len(order.items),
        "region": order.meta.get("region", "")
    }
    text = json.dumps(payload, ensure_ascii=False)
    print(text)
    return text
