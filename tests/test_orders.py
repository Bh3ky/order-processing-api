from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order


def test_create_order_returns_201(client: TestClient):
    response = client.post(
        "/api/v1/orders",
        json={
            "items": [
                {
                    "product_id": "550e8400-e29b-41d4-a716-446655440000",
                    "quantity": 2,
                }
            ]
        },
    )

    assert response.status_code == 201
    body = response.json()

    assert "id" in body
    assert body["status"] == "pending"
    assert body["total_amount"] == 0
    assert "created_at" in body
    assert "updated_at" in body


@pytest.mark.asyncio
async def test_create_order_persists_order(
    client: TestClient,
    db_session: AsyncSession,
):
    response = client.post(
        "/api/v1/orders",
        json={
            "items": [
                {"product_id": "550e8400-e29b-41d4-a716-446655440000", "quantity": 2}
            ]
        },
    )

    assert response.status_code == 201
    body = response.json()

    order_id = UUID(body["id"])
    result = await db_session.execute(select(Order).where(Order.id == order_id))

    persisted_order = result.scalar_one_or_none()
    assert persisted_order is not None
    assert persisted_order.id == order_id
    assert persisted_order.status == "pending"


@pytest.mark.asyncio
async def test_orders_table_empty_at_start(db_session: AsyncSession):
    # verify that the previous test's transaction was rolled back.
    result = await db_session.execute(select(Order))
    orders = result.scalars().all()

    assert orders == []


def test_empty_order_returns_422(client: TestClient):
    response = client.post(
        "/api/v1/orders",
        json={"items": []},
    )

    assert response.status_code == 422
    body = response.json()
    assert "detail" in body


@pytest.mark.parametrize(
    "quantity, description",
    [
        (0, "boundary zero"),
        (-1, "below boundary"),
    ],
)
def test_order_with_zero_quantity_returns_422(
    client: TestClient, quantity: int, description: str
):
    response = client.post(
        "/api/v1/orders",
        json={
            "items": [
                {
                    "product_id": "550e8400-e29b-41d4-a716-446655440000",
                    "quantity": quantity,
                }
            ]
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert "detail" in body


def test_order_with_invalid_product_id_returns_422(client: TestClient):
    response = client.post(
        "/api/v1/orders",
        json={
            "items": [
                {
                    "product_id": "not-a-uuid",
                    "quantity": 2,
                }
            ]
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
