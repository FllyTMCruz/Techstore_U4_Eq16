import pytest
from fastapi.testclient import TestClient
from app.api import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_server_state():
    """Reinicia el repositorio en memoria antes de cada prueba."""
    client.post("/reset")


def test_get_order_200():
    response = client.get("/orders/O001")
    assert response.status_code == 200
    data = response.json()
    assert "message" not in data
    assert data["id"] == "O001"
    assert data["status"] == "DRAFT"
    assert data["units"] == 4


def test_get_order_404():
    response = client.get("/orders/O999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Pedido no encontrado"


def test_confirm_order_200():
    response = client.post("/orders/O001/confirm")
    assert response.status_code == 200
    assert response.json()["message"] == "Pedido confirmado correctamente."
    assert response.json()["status"] == "CONFIRMED"


def test_confirm_order_409_doble_confirmacion():
    # Primera confirmación exitosa
    client.post("/orders/O001/confirm")
    # Segunda confirmación produce conflicto
    response = client.post("/orders/O001/confirm")
    assert response.status_code == 409


def test_confirm_order_422_pedido_vacio():
    # O007 no tiene artículos
    response = client.post("/orders/O007/confirm")
    assert response.status_code == 422


def test_ship_order_200():
    client.post("/orders/O001/confirm")
    response = client.post("/orders/O001/ship", json={"tracking_number": "GUIA-TEST-01"})
    assert response.status_code == 200
    assert "message" not in response.json()
    assert response.json()["status"] == "SHIPPED"


def test_ship_order_422_sin_guia():
    client.post("/orders/O001/confirm")
    response = client.post("/orders/O001/ship", json={"tracking_number": ""})
    assert response.status_code == 422


def test_cancel_order_409_desde_shipped():
    client.post("/orders/O001/confirm")
    client.post("/orders/O001/ship", json={"tracking_number": "GUIA-TEST-01"})
    response = client.post("/orders/O001/cancel", json={"reason": "Cancelación tardía"})
    assert response.status_code == 409