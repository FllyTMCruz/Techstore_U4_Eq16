from decimal import Decimal
from app.domain import Order

# ---------------------------------------------------------
# 1. Clase Base y Compositores (AND, OR, NOT)
# ---------------------------------------------------------
class Specification:
    def is_satisfied_by(self, order: Order) -> bool:
        raise NotImplementedError

    def __and__(self, other: "Specification") -> "Specification":
        return AndSpec(self, other)

    def __or__(self, other: "Specification") -> "Specification":
        return OrSpec(self, other)

    def __invert__(self) -> "Specification":
        return NotSpec(self)


class AndSpec(Specification):
    def __init__(self, left: Specification, right: Specification):
        self.left = left
        self.right = right

    def is_satisfied_by(self, order: Order) -> bool:
        return self.left.is_satisfied_by(order) and self.right.is_satisfied_by(order)


class OrSpec(Specification):
    def __init__(self, left: Specification, right: Specification):
        self.left = left
        self.right = right

    def is_satisfied_by(self, order: Order) -> bool:
        return self.left.is_satisfied_by(order) or self.right.is_satisfied_by(order)


class NotSpec(Specification):
    def __init__(self, spec: Specification):
        self.spec = spec

    def is_satisfied_by(self, order: Order) -> bool:
        return not self.spec.is_satisfied_by(order)


# ---------------------------------------------------------
# 2. Reglas Concretas del Negocio
# ---------------------------------------------------------
class MinimumAmountSpec(Specification):
    def __init__(self, min_amount: Decimal):
        self.min_amount = min_amount

    def is_satisfied_by(self, order: Order) -> bool:
        # La regla exige > (estricto), no >=
        return order.total.amount > self.min_amount


class VIPCustomerSpec(Specification):
    def is_satisfied_by(self, order: Order) -> bool:
        return order.customer.is_vip


class MinimumUnitsSpec(Specification):
    def __init__(self, min_units: int):
        self.min_units = min_units

    def is_satisfied_by(self, order: Order) -> bool:
        return order.units >= self.min_units


class ActivePromotionSpec(Specification):
    def is_satisfied_by(self, order: Order) -> bool:
        return order.has_promotion


# ---------------------------------------------------------
# 3. Composición de Reglas de Descuento
# ---------------------------------------------------------
ten_percent_discount_spec = (
    MinimumAmountSpec(Decimal("500"))
    & VIPCustomerSpec()
    & MinimumUnitsSpec(4)
    & ~ActivePromotionSpec()
)

five_percent_discount_spec = (
    MinimumAmountSpec(Decimal("5000"))
    & ~ActivePromotionSpec()
)

def calculate_discount_percentage(order: Order) -> Decimal:
    """Aplica primero 10% si se cumple; de lo contrario 5%; si no, 0%."""
    if ten_percent_discount_spec.is_satisfied_by(order):
        return Decimal("0.10")
    if five_percent_discount_spec.is_satisfied_by(order):
        return Decimal("0.05")
    return Decimal("0.00")