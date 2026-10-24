from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from datetime import datetime, timezone

# ---------------------------------------------------------
# 1. Jerarquía de Excepciones de Dominio
# ---------------------------------------------------------
class DomainException(Exception): pass
class InvalidOrderData(DomainException): pass
class InvalidOrderTransition(DomainException): pass
class OrderItemLimitExceeded(DomainException): pass

# ---------------------------------------------------------
# 2. Value Object: Money
# ---------------------------------------------------------
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

# ---------------------------------------------------------
# 3. Customer y OrderItem
# ---------------------------------------------------------
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

# ---------------------------------------------------------
# 4. Domain Event
# ---------------------------------------------------------
@dataclass(frozen=True)
class DomainEvent:
    name: str
    order_id: str
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

# ---------------------------------------------------------
# 5. Aggregate Root: Order con Máquina de Estados
# ---------------------------------------------------------
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
    events: list[DomainEvent] = field(default_factory=list)

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

    # Transición: DRAFT -> CONFIRMED
    def confirm(self):
        if self.status != OrderStatus.DRAFT:
            raise InvalidOrderTransition(f"No se puede confirmar un pedido en estado {self.status.value}")
        if not self.items:
            raise InvalidOrderData("No se puede confirmar un pedido sin artículos")
        if not self.customer.active:
            raise InvalidOrderData("No se puede confirmar un pedido de un cliente inactivo")
        self.status = OrderStatus.CONFIRMED
        self.events.append(DomainEvent("OrderConfirmed", self.id))

    # Transición: CONFIRMED -> SHIPPED
    def ship(self, tracking_number: str):
        if self.status != OrderStatus.CONFIRMED:
            raise InvalidOrderTransition(f"No se puede enviar un pedido en estado {self.status.value}")
        if not tracking_number or not tracking_number.strip():
            raise InvalidOrderData("Se requiere un número de guía válido para el envío")
        self.status = OrderStatus.SHIPPED
        self.events.append(DomainEvent("OrderShipped", self.id))

    # Transición: CONFIRMED -> CANCELLED
    def cancel(self, reason: str):
        if self.status != OrderStatus.CONFIRMED:
            raise InvalidOrderTransition(f"No se puede cancelar un pedido en estado {self.status.value}")
        if not reason or not reason.strip():
            raise InvalidOrderData("Se requiere un motivo para cancelar el pedido")
        self.status = OrderStatus.CANCELLED
        self.events.append(DomainEvent("OrderCancelled", self.id))

    # Transición: SHIPPED -> DELIVERED
    def deliver(self):
        if self.status != OrderStatus.SHIPPED:
            raise InvalidOrderTransition(f"No se puede entregar un pedido en estado {self.status.value}")
        self.status = OrderStatus.DELIVERED
        self.events.append(DomainEvent("OrderDelivered", self.id))

    # Transición: SHIPPED -> RETURNED
    def return_order(self):
        if self.status != OrderStatus.SHIPPED:
            raise InvalidOrderTransition(f"No se puede devolver un pedido en estado {self.status.value}")
        self.status = OrderStatus.RETURNED
        self.events.append(DomainEvent("OrderReturned", self.id))