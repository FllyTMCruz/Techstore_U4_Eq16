from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from cargar_csv import load_fixture
from app.domain import (
    InvalidOrderTransition,
    InvalidOrderData,
    OrderItemLimitExceeded,
    OrderStatus,
)

app = FastAPI(
    title="TechStore U4 API",
    description="API REST para la administración del ciclo de vida de pedidos de TechStore",
    version="1.0.0",
)

# Repositorio en memoria cargado desde los archivos CSV (Sección 11)
orders = load_fixture()


# ---------------------------------------------------------
# DTOs (Data Transfer Objects) con Pydantic
# ---------------------------------------------------------
class ShipRequest(BaseModel):
    tracking_number: str


class CancelRequest(BaseModel):
    reason: str


# ---------------------------------------------------------
# Endpoints de Consulta y Transiciones de Estado
# ---------------------------------------------------------
@app.get("/orders/{order_id}", tags=["Pedidos"])
def get_order(order_id: str):
    """Consulta el detalle y estado actual de un pedido."""
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return {
        "id": order.id,
        "customer_id": order.customer.id,
        "is_vip": order.customer.is_vip,
        "customer_active": order.customer.active,
        "status": order.status.value,
        "has_promotion": order.has_promotion,
        "units": order.units,
        "total": float(order.total.amount),
        "currency": order.total.currency,
        "items": [
            {
                "sku": item.sku,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price.amount),
                "subtotal": float(item.subtotal.amount),
            }
            for item in order.items
        ],
        "events": [
            {"name": e.name, "occurred_at": e.occurred_at.isoformat()}
            for e in order.events
        ],
    }


@app.post("/orders/{order_id}/confirm", tags=["Máquina de Estados"])
def confirm_order(order_id: str):
    """Confirma un pedido en estado DRAFT."""
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    try:
        order.confirm()
    except InvalidOrderTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except InvalidOrderData as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {
        "message": "Pedido confirmado correctamente.",
        "id": order.id,
        "status": order.status.value,
    }


@app.post("/orders/{order_id}/ship", tags=["Máquina de Estados"])
def ship_order(order_id: str, payload: ShipRequest):
    """Envía un pedido CONFIRMED asociando su número de guía."""
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    try:
        order.ship(payload.tracking_number)
    except InvalidOrderTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except InvalidOrderData as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {
        "id": order.id,
        "status": order.status.value,
        "tracking_number": payload.tracking_number,
    }


@app.post("/orders/{order_id}/cancel", tags=["Máquina de Estados"])
def cancel_order(order_id: str, payload: CancelRequest):
    """Cancela un pedido CONFIRMED registrando el motivo."""
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    try:
        order.cancel(payload.reason)
    except InvalidOrderTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except InvalidOrderData as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {
        "id": order.id,
        "status": order.status.value,
        "reason": payload.reason,
    }


@app.post("/orders/{order_id}/deliver", tags=["Máquina de Estados"])
def deliver_order(order_id: str):
    """Registra la entrega exitosa de un pedido SHIPPED."""
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    try:
        order.deliver()
    except InvalidOrderTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except InvalidOrderData as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {
        "id": order.id,
        "status": order.status.value,
    }


@app.post("/orders/{order_id}/return", tags=["Máquina de Estados"])
def return_order(order_id: str):
    """Registra la devolución de un pedido SHIPPED."""
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    try:
        order.return_order()
    except InvalidOrderTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except InvalidOrderData as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {
        "id": order.id,
        "status": order.status.value,
    }


@app.post("/reset", tags=["Utilidades"])
def reset_fixtures():
    """Recarga los pedidos originales en memoria sin reiniciar el servidor."""
    global orders
    orders = load_fixture()
    return {"total_orders": len(orders)}