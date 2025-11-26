from dataclasses import dataclass, field
from typing import List, Dict


@dataclass(frozen=True)
class Item:
    sku: str
    price: float


@dataclass
class Cart:
    items: List[Item] = field(default_factory=list)

    def add(self, item: Item) -> None:
        self.items.append(item)

    def total(self) -> float:
        return sum(i.price for i in self.items)


@dataclass(frozen=True)
class User:
    id: str
    tier: str  # "basic", "vip"


@dataclass
class Order:
    user: User
    items: List[Item]
    amount: float
    meta: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "user": {"id": self.user.id, "tier": self.user.tier},
            "items": [{"sku": i.sku, "price": i.price} for i in self.items],
            "amount": self.amount,
            "meta": self.meta,
        }
