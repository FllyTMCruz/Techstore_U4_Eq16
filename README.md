# TechStore U4 – Núcleo de negocio

Equipo 16 · Componentes de Lógica de Negocios · FIME UANL

Sistema de pedidos en memoria (sin base de datos): lee CSV, aplica reglas de
descuento con Specification Pattern, controla el ciclo de vida del pedido con
Domain Events y expone una API REST con FastAPI.

## Estructura
```
app/domain.py          Money, Customer, OrderItem, Order, eventos y excepciones
app/specifications.py  Specifications (AND, OR, NOT) y reglas de descuento
app/api.py             API FastAPI
cargar_csv.py          Cargador de datos (load_fixture)
datos/                 5 CSV (clientes, productos, pedidos, detalle, escenarios)
tests/                 Pruebas pytest (dominio y API)
```

## Instalación (Python 3.11+)
```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS / Linux:      source .venv/bin/activate
python -m pip install fastapi uvicorn pytest httpx
```

## Ejecución
```bash
python cargar_csv.py                 # carga los 16 pedidos en DRAFT
python -m pytest -q                  # corre las pruebas
uvicorn app.api:app --reload         # API en http://127.0.0.1:8000/docs
```

## Reglas de negocio
- Máximo 20 unidades por pedido (suma de cantidades, no renglones).
- Dinero con `Decimal`, moneda MXN, sin montos negativos.
- Descuento 10 %: VIP, total > 500, al menos 4 unidades y sin promoción activa.
- Descuento 5 %: total > 5000 y sin promoción activa.
- Si se cumplen ambas, aplica 10 %.
- Confirmar exige artículos y cliente activo.
- Enviar exige guía no vacía; cancelar exige motivo no vacío.

## Estados y eventos
DRAFT → CONFIRMED → SHIPPED → DELIVERED
CONFIRMED → CANCELLED · SHIPPED → RETURNED

Eventos: OrderConfirmed, OrderShipped, OrderCancelled, OrderDelivered,
OrderReturned. Solo se registran después de una transición válida.

## Endpoints
| Método | Ruta | Códigos |
|---|---|---|
| GET | /orders/{id} | 200, 404 |
| POST | /orders/{id}/confirm | 200, 404, 409, 422 |
| POST | /orders/{id}/ship | 200, 404, 409, 422 |
| POST | /orders/{id}/cancel | 200, 404, 409, 422 |
| POST | /reset | 200 |

404 = no existe · 409 = estado no permite la operación · 422 = datos inválidos.

## Evidencias
Capturas, bitácora E01–E15 y reflexión en `Reporte_Final_TechStore_U4_Eq16.docx`.
