from fastapi.testclient import TestClient


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
