from dataclasses import dataclass
from typing import List

from app.models import Item, User, Cart


@dataclass(frozen=True)
class Defaults:
    base_price: float = 10.0


def make_user(uid: str = "U1", tier: str = "basic") -> User:
    return User(id=uid, tier=tier)


def make_items(n: int = 1, base: float = Defaults.base_price) -> List[Item]:
    return [Item(sku=f"SKU-{i}", price=base + i) for i in range(n)]


def make_cart(items: List[Item] = None) -> Cart:
    c = Cart()
    if items:
        for i in items:
            c.add(i)
    return c
