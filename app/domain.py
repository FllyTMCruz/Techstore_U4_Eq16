from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from datetime import datetime, timezone

# Excepciones de Dominio (Sección 6.1)
class DomainException(Exception): pass
class InvalidOrderData(DomainException): pass
class InvalidOrderTransition(DomainException): pass
class OrderItemLimitExceeded(DomainException): pass

# 6.1 Money: Value Object inmutable
@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "MXN"

    def __post_init__(self):
        if not self.amount.is_finite() or self.amount < 0:
            raise InvalidOrderData("Monto inválido")

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise InvalidOrderData("Monedas distintas")
        return Money(self.amount + other.amount, self.currency)

# 6.2 Customer y OrderItem
@dataclass(frozen=True)
class Customer:
    id: str
    is_vip: bool = False
    active: bool = True

@dataclass(frozen=True)
class OrderItem:
    sku: str
    quantity: int
    unit_price: Money

    def __post_init__(self):
        if not self.sku.strip() or self.quantity <= 0:
            raise InvalidOrderData("Artículo inválido")

    @property
    def subtotal(self) -> Money:
        return Money(self.unit_price.amount * self.quantity)

# 6.3 Order como Aggregate Root
class OrderStatus(str, Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    RETURNED = "RETURNED"

@dataclass
class Order:
    customer: Customer
    id: str
    has_promotion: bool = False
    status: OrderStatus = OrderStatus.DRAFT
    items: list[OrderItem] = field(default_factory=list)
    events: list = field(default_factory=list)

    @property
    def units(self) -> int:
        return sum(item.quantity for item in self.items)

    @property
    def total(self) -> Money:
        amount = sum((x.subtotal.amount for x in self.items), Decimal("0"))
        return Money(amount)

    def add_item(self, item: OrderItem):
        if self.status != OrderStatus.DRAFT:
            raise InvalidOrderTransition("Solo DRAFT admite artículos")
        if self.units + item.quantity > 20:
            raise OrderItemLimitExceeded("Máximo 20 unidades")
        if item.unit_price.currency != "MXN":
            raise InvalidOrderData("Solo MXN")
        self.items.append(item)