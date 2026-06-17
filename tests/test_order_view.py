from uuid import uuid4
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status

from src.models.order import OrderStatus, Order
from tests.conftest import create_jwt_token


@pytest.mark.asyncio
async def test_orders_list_returns_own_orders_paginated(
        async_client,
        buyer_id,
):
    token = create_jwt_token(buyer_id)

    orders_payload = {
        "items": [
            {
                "id": str(uuid4()),
                "number": "ORD-001",
                "buyer_id": str(buyer_id),
                "status": OrderStatus.CREATED.value,
                "status_history": [],
                "items": [],
                "subtotal": 1000,
                "delivery_cost": 0,
                "total": 1000,
                "address": None,
                "payment_method": None,
                "comment": None,
                "cancel_reason": None,
                "created_at": "2026-06-17T12:00:00",
                "paid_at": None,
                "delivered_at": None,
            },
            {
                "id": str(uuid4()),
                "number": "ORD-002",
                "buyer_id": str(buyer_id),
                "status": OrderStatus.PAID.value,
                "status_history": [],
                "items": [],
                "subtotal": 2000,
                "delivery_cost": 0,
                "total": 2000,
                "address": None,
                "payment_method": None,
                "comment": None,
                "cancel_reason": None,
                "created_at": "2026-06-17T12:00:00",
                "paid_at": None,
                "delivered_at": None,
            },
        ],
        "total_count": 2,
        "limit": 10,
        "offset": 0,
    }

    with patch(
            "src.services.order_service.OrderService.get_orders",
            new_callable=AsyncMock,
    ) as mock_get_orders:
        mock_get_orders.return_value = orders_payload

        response = await async_client.get(
            "/api/v1/orders?limit=10&offset=0",
            headers={
                "Authorization": f"Bearer {token}",
            },
        )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert data["total_count"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_order_detail_shows_fixed_prices(
        async_client,
        buyer_id,
):
    token = create_jwt_token(buyer_id)
    order_id = uuid4()

    order_payload = {
        "id": str(order_id),
        "number": "ORD-001",
        "buyer_id": str(buyer_id),
        "status": OrderStatus.PAID.value,
        "status_history": [],
        "subtotal": 5000,
        "delivery_cost": 0,
        "total": 5000,
        "address": None,
        "payment_method": None,
        "comment": None,
        "cancel_reason": None,
        "created_at": "2026-06-17T12:00:00",
        "paid_at": None,
        "delivered_at": None,
        "items": [
            {
                "sku_id": str(uuid4()),
                "product_id": str(uuid4()),
                "name": "Test Product",
                "sku_code": "SKU-001",
                "quantity": 1,
                "unit_price": 5000,
                "line_total": 5000,
                "image_url": None,
            }
        ],
    }

    with patch(
            "src.services.order_service.OrderService.get_order",
            new_callable=AsyncMock,
    ) as mock_get_order:
        mock_get_order.return_value = order_payload

        response = await async_client.get(
            f"/api/v1/orders/{order_id}",
            headers={
                "Authorization": f"Bearer {token}",
            },
        )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert len(data["items"]) == 1
    assert data["items"][0]["unit_price"] == 5000


@pytest.mark.asyncio
async def test_other_user_order_returns_404_not_403(
        async_client,
        test_db,
):
    owner_id = uuid4()
    stranger_id = uuid4()

    order = Order(
        id=uuid4(),
        buyer_id=owner_id,
        address_id=uuid4(),
        payment_method_id=uuid4(),
        number="ORD-1",
        subtotal=1000,
        delivery_cost=0,
        total=1000,
        idempotency_key=uuid4(),
        status=OrderStatus.CREATED,
    )

    test_db.add(order)
    await test_db.commit()

    token = create_jwt_token(stranger_id)

    response = await async_client.get(
        f"/api/v1/orders/{order.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND