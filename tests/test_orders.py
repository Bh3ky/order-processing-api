import uuid
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem
from app.models.product import Product


@pytest.mark.asyncio
async def test_create_order_returns_201(
    client: TestClient,
    db_session: AsyncSession,
):
    product = Product(
        sku="TEST-SKU-RETURN-201",
        name="Test Product for 201",
        price=Decimal("19.99"),
    )

    db_session.add(product)
    # send the INSERT to PostgreSQL
    await db_session.flush()

    response = client.post(
        "/api/v1/orders",
        json={
            "items": [
                {
                    "product_id": str(product.id),
                    "quantity": 2,
                }
            ]
        },
    )

    assert response.status_code == 201
    body = response.json()

    assert "id" in body
    assert body["status"] == "pending"
    assert body["total_amount"] == 39.98
    assert "created_at" in body
    assert "updated_at" in body


@pytest.mark.asyncio
async def test_create_order_persists_order(
    client: TestClient,
    db_session: AsyncSession,
):
    product = Product(
        sku="TEST-SKU-PERSIST",
        name="Persist Test Product",
        price=Decimal("19.99"),
    )

    db_session.add(product)
    await db_session.flush()

    response = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": str(product.id), "quantity": 2}]},
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


@pytest.mark.asyncio
async def test_create_order_with_existing_product(
    client: TestClient,
    db_session: AsyncSession,
):
    product = Product(
        sku="TEST-SKU-001",
        name="Test Product",
        price=Decimal("19.99"),
    )

    # place the ORM object into SQLAlchemy's session
    db_session.add(product)
    # sends the INSERT to PostgreSQL inside the current transaction
    await db_session.flush()

    response = client.post(
        "/api/v1/orders",
        json={
            "items": [
                {
                    "product_id": str(product.id),
                    "quantity": 1,
                }
            ]
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"


def test_create_order_with_nonexistent_product(client: TestClient):
    # generate valid UUID that does not correspond to any product in the database
    nonexistent_product_id = uuid.uuid4()

    response = client.post(
        "/api/v1/orders",
        json={
            "items": [
                {
                    "product_id": str(nonexistent_product_id),
                    "quantity": 1,
                }
            ]
        },
    )

    assert response.status_code == 404

    body = response.json()
    assert "detail" in body


@pytest.mark.asyncio
async def test_nonexistent_product_does_not_create_order(
    client: TestClient,
    db_session: AsyncSession,
):
    nonexistent_product_id = uuid.uuid4()

    response = client.post(
        "/api/v1/orders",
        json={
            "items": [
                {
                    "product_id": str(nonexistent_product_id),
                    "quantity": 1,
                }
            ]
        },
    )

    assert response.status_code == 404

    # verify that no order was created in the database
    result = await db_session.execute(select(Order))
    orders = result.scalars().all()
    assert orders == []


@pytest.mark.asyncio
async def test_create_order_fails_if_any_product_does_not_exist(
    client: TestClient,
    db_session: AsyncSession,
):
    # create a real product
    real_product = Product(
        sku="TEST-SKU-002",
        name="Real Product",
        price=Decimal("19.99"),
    )

    db_session.add(real_product)
    await db_session.flush()

    # generate a UUID for a nonexistent product
    nonexistent_product_id = uuid.uuid4()

    response = client.post(
        "/api/v1/orders",
        json={
            "items": [
                {
                    "product_id": str(real_product.id),
                    "quantity": 1,
                },
                {
                    "product_id": str(nonexistent_product_id),
                    "quantity": 1,
                },
            ]
        },
    )

    assert response.status_code == 404
    # verify that no order was created in the database
    result = await db_session.execute(select(Order))
    orders = result.scalars().all()
    assert orders == []


@pytest.mark.asyncio
async def test_create_order_persists_order_item(
    client: TestClient,
    db_session: AsyncSession,
):
    # create a real product
    product = Product(
        sku="TEST-SKU-003",
        name="Persist Test Product",
        price=Decimal("19.99"),
    )

    # flush it
    db_session.add(product)
    await db_session.flush()

    # `POST` /orders
    response = client.post(
        "/api/v1/orders",
        json={
            "items": [
                {
                    "product_id": str(product.id),
                    "quantity": 1,
                }
            ]
        },
    )

    # assert response is 201
    assert response.status_code == 201

    # query OrderItem
    result = await db_session.execute(select(OrderItem))
    order_items = result.scalars().all()

    # assert exactly one row exists
    assert len(order_items) == 1

    order_item = order_items[0]

    assert order_item.product_id == product.id
    assert order_item.quantity == 1
    assert order_item.unit_price == Decimal("19.99")
    assert order_item.line_total == Decimal("19.99")


@pytest.mark.asyncio
async def test_create_order_calculates_total_amount(
    client: TestClient,
    db_session: AsyncSession,
):
    product1 = Product(
        sku="TEST-SKU-004",
        name="Test Product 1",
        price=Decimal("19.99"),
    )
    product2 = Product(
        sku="TEST-SKU-005",
        name="Test Product 2",
        price=Decimal("5.99"),
    )

    db_session.add_all([product1, product2])
    await db_session.flush()

    response = client.post(
        "/api/v1/orders",
        json={
            "items": [
                {
                    "product_id": str(product1.id),
                    "quantity": 2,
                },
                {
                    "product_id": str(product2.id),
                    "quantity": 3,
                },
            ]
        },
    )

    assert response.status_code == 201

    result = await db_session.execute(select(Order))
    persisted_order = result.scalar_one()

    assert persisted_order.total_amount == Decimal("57.95")

    result = await db_session.execute(select(OrderItem))
    order_items = result.scalars().all()

    assert len(order_items) == 2
