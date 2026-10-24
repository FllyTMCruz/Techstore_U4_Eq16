import pytest
from decimal import Decimal
from app.domain import (
    Money,
    Customer,
    OrderItem,
    Order,
    OrderStatus,
    InvalidOrderData,
    InvalidOrderTransition,
    OrderItemLimitExceeded,
)
from app.specifications import calculate_discount_percentage
from cargar_csv import load_fixture


# ---------------------------------------------------------
# 1. Pruebas de Value Objects e Invariantes
# ---------------------------------------------------------
def test_money_negativo():
    """Valida que Money no admita montos negativos."""
    with pytest.raises(InvalidOrderData):
        Money(Decimal("-1.00"))


def test_money_monedas_distintas():
    """Valida que no se puedan sumar monedas diferentes."""
    m1 = Money(Decimal("100.00"), "MXN")
    m2 = Money(Decimal("50.00"), "USD")
    with pytest.raises(InvalidOrderData):
        m1.add(m2)


def test_order_item_invalido():
    """Valida que un artículo no admita cantidad <= 0 ni SKU vacío."""
    precio = Money(Decimal("100.00"))
    with pytest.raises(InvalidOrderData):
        OrderItem("", 2, precio)
    with pytest.raises(InvalidOrderData):
        OrderItem("SKU001", 0, precio)


# ---------------------------------------------------------
# 2. Pruebas de Carga Inicial y Límites de Unidades
# ---------------------------------------------------------
def test_pedido_o001_inicia_draft():
    """Valida que O001 cargue en DRAFT con 4 unidades y $2100.00."""
    orders = load_fixture()
    o = orders["O001"]
    assert o.status == OrderStatus.DRAFT
    assert o.units == 4
    assert o.total.amount == Decimal("2100.00")


def test_limite_21_unidades_excedido():
    """Valida que agregar artículos superando 20 unidades lance OrderItemLimitExceeded."""
    orders = load_fixture()
    # O009 tiene 19 unidades cargadas inicialmente
    o = orders["O009"]
    assert o.units == 19
    item_extra = OrderItem("SKU003", 2, Money(Decimal("120.00")))
    with pytest.raises(OrderItemLimitExceeded):
        o.add_item(item_extra)


# ---------------------------------------------------------
# 3. Pruebas de Reglas con Specification Pattern
# ---------------------------------------------------------
def test_descuento_vip_10_porciento():
    """O001 cumple: VIP, total > 500, unidades >= 4, sin promoción -> 10%."""
    orders = load_fixture()
    assert calculate_discount_percentage(orders["O001"]) == Decimal("0.10")


def test_descuento_general_5_porciento():
    """O006 cumple: no VIP, total > 5000, sin promoción -> 5%."""
    orders = load_fixture()
    assert calculate_discount_percentage(orders["O006"]) == Decimal("0.05")


def test_promocion_activa_bloquea_descuento():
    """O005 tiene promoción activa, por lo que no recibe descuento."""
    orders = load_fixture()
    assert calculate_discount_percentage(orders["O005"]) == Decimal("0.00")


def test_monto_frontera_exacto_500_no_aplica():
    """O010 tiene total exactamente 500.00; como el umbral es > 500 estricto, no aplica."""
    orders = load_fixture()
    assert calculate_discount_percentage(orders["O10" if "O10" in orders else "O010"]) == Decimal("0.00")


# ---------------------------------------------------------
# 4. Pruebas de la Máquina de Estados y Transiciones
# ---------------------------------------------------------
def test_confirmar_cliente_inactivo_falla():
    """O003 tiene cliente inactivo (activo=0); no puede confirmarse."""
    orders = load_fixture()
    with pytest.raises(InvalidOrderData):
        orders["O003"].confirm()


def test_confirmar_pedido_vacio_falla():
    """O007 no tiene artículos; no puede confirmarse."""
    orders = load_fixture()
    with pytest.raises(InvalidOrderData):
        orders["O007"].confirm()


def test_confirmacion_doble_falla():
    """Confirmar un pedido CONFIRMED debe lanzar InvalidOrderTransition."""
    orders = load_fixture()
    o = orders["O013"]
    o.confirm()
    assert o.status == OrderStatus.CONFIRMED
    assert len(o.events) == 1
    with pytest.raises(InvalidOrderTransition):
        o.confirm()
    # Los eventos no deben incrementarse tras un fallo
    assert len(o.events) == 1


def test_envio_sin_guia_falla():
    """Llamar a ship sin número de guía debe fallar."""
    orders = load_fixture()
    o = orders["O012"]
    o.confirm()
    with pytest.raises(InvalidOrderData):
        o.ship("")
    assert o.status == OrderStatus.CONFIRMED


def test_cancelacion_desde_shipped_falla():
    """No se permite cancelar un pedido que ya fue enviado."""
    orders = load_fixture()
    o = orders["O014"]
    o.confirm()
    o.ship("GUIA-123")
    assert o.status == OrderStatus.SHIPPED
    with pytest.raises(InvalidOrderTransition):
        o.cancel("Ya no lo quiero")
    assert o.status == OrderStatus.SHIPPED


def test_flujo_completo_entrega():
    """DRAFT -> CONFIRMED -> SHIPPED -> DELIVERED con sus 3 eventos."""
    orders = load_fixture()
    o = orders["O016"]
    o.confirm()
    o.ship("TRACK-DELIVER")
    o.deliver()
    assert o.status == OrderStatus.DELIVERED
    assert [e.name for e in o.events] == ["OrderConfirmed", "OrderShipped", "OrderDelivered"]


def test_flujo_completo_devolucion():
    """DRAFT -> CONFIRMED -> SHIPPED -> RETURNED con sus 3 eventos."""
    orders = load_fixture()
    o = orders["O015"]
    o.confirm()
    o.ship("TRACK-RETURN")
    o.return_order()
    assert o.status == OrderStatus.RETURNED
    assert [e.name for e in o.events] == ["OrderConfirmed", "OrderShipped", "OrderReturned"]