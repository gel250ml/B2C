from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.models import (
    Address,
    Buyer,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    PaymentMethodType,
)
from src.services.b2b_inventory_client import B2BInventoryClient, B2BUnavailableError
from tests.conftest import create_jwt_token


async def create_order(test_db, buyer_id=None, status=OrderStatus.PAID):
    buyer_id = buyer_id or uuid4()
    address_id = uuid4()
    payment_method_id = uuid4()
    order_id = uuid4()
    sku_id = uuid4()

    buyer = Buyer(
        id=buyer_id,
        email=f"{buyer_id}@example.com",
        password_hash="hash",
        first_name="Ivan",
        last_name="Buyer",
    )
    address = Address(
        id=address_id,
        buyer_id=buyer_id,
        country="RU",
        city="Moscow",
        street="Tverskaya",
        building="1",
        recipient_name="Ivan Buyer",
        recipient_phone="79999999999",
    )
    payment_method = PaymentMethod(
        id=payment_method_id,
        buyer_id=buyer_id,
        type=PaymentMethodType.CARD,
        card_last4="5539",
        card_brand="VISA",
    )
    order = Order(
        id=order_id,
        buyer_id=buyer_id,
        address_id=address_id,
        payment_method_id=payment_method_id,
        number=f"ORD-{order_id.hex[:8]}",
        status=status,
        subtotal=200,
        delivery_cost=0,
        total=200,
        idempotency_key=uuid4(),
        paid_at=datetime.now(UTC).replace(tzinfo=None) if status != OrderStatus.CREATED else None,
    )
    item = OrderItem(
        order_id=order_id,
        product_id=uuid4(),
        sku_id=sku_id,
        name="Test product",
        sku_code="SKU-1",
        quantity=2,
        unit_price=100,
        line_total=200,
        image_url="https://example.com/image.jpg",
    )

    test_db.add_all([buyer, address, payment_method, order, item])
    await test_db.commit()
    return order_id, buyer_id, sku_id


@pytest.mark.asyncio
async def test_cancel_paid_order_transitions_to_cancelled(async_client, test_db, monkeypatch):
    order_id, buyer_id, sku_id = await create_order(test_db, status=OrderStatus.PAID)
    calls = []

    async def fake_unreserve(self, order_id, items):
        calls.append({"order_id": order_id, "items": items})

    monkeypatch.setattr(B2BInventoryClient, "unreserve", fake_unreserve)

    response = await async_client.post(
        f"/api/v1/orders/{order_id}/cancel",
        headers={"Authorization": f"Bearer {create_jwt_token(buyer_id)}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(order_id)
    assert body["status"] == "CANCELLED"
    assert body["cancel_reason"] is None
    assert body["items"][0]["sku_id"] == str(sku_id)
    assert [item["status"] for item in body["status_history"]] == ["CANCEL_PENDING", "CANCELLED"]
    assert calls == [
        {
            "order_id": order_id,
            "items": [{"sku_id": str(sku_id), "quantity": 2}],
        }
    ]


@pytest.mark.asyncio
async def test_unreserve_failure_transitions_to_cancel_pending(async_client, test_db, monkeypatch):
    order_id, buyer_id, _ = await create_order(test_db, status=OrderStatus.PAID)

    async def fake_unreserve(self, order_id, items):
        raise B2BUnavailableError("B2B down")

    monkeypatch.setattr(B2BInventoryClient, "unreserve", fake_unreserve)

    response = await async_client.post(
        f"/api/v1/orders/{order_id}/cancel",
        headers={"Authorization": f"Bearer {create_jwt_token(buyer_id)}"},
        json={"reason": "Передумал"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "CANCEL_PENDING"
    assert body["cancel_reason"] == "Передумал"
    assert [item["status"] for item in body["status_history"]] == ["CANCEL_PENDING"]


@pytest.mark.asyncio
async def test_cancel_assembling_order_transitions_to_cancelled(async_client, test_db, monkeypatch):
    order_id, buyer_id, sku_id = await create_order(test_db, status=OrderStatus.ASSEMBLING)
    calls = []

    async def fake_unreserve(self, order_id, items):
        calls.append({"order_id": order_id, "items": items})

    monkeypatch.setattr(B2BInventoryClient, "unreserve", fake_unreserve)

    response = await async_client.post(
        f"/api/v1/orders/{order_id}/cancel",
        headers={"Authorization": f"Bearer {create_jwt_token(buyer_id)}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "CANCELLED"
    assert body["items"][0]["sku_id"] == str(sku_id)
    assert [item["status"] for item in body["status_history"]] == ["CANCEL_PENDING", "CANCELLED"]
    assert calls == [
        {
            "order_id": order_id,
            "items": [{"sku_id": str(sku_id), "quantity": 2}],
        }
    ]


@pytest.mark.asyncio
async def test_cancel_delivering_order_transitions_to_cancelled(async_client, test_db, monkeypatch):
    order_id, buyer_id, _ = await create_order(test_db, status=OrderStatus.DELIVERING)
    called = False

    async def fake_unreserve(self, order_id, items):
        nonlocal called
        called = True

    monkeypatch.setattr(B2BInventoryClient, "unreserve", fake_unreserve)

    response = await async_client.post(
        f"/api/v1/orders/{order_id}/cancel",
        headers={"Authorization": f"Bearer {create_jwt_token(buyer_id)}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert called is True


@pytest.mark.asyncio
async def test_cancel_delivered_order_returns_409(async_client, test_db, monkeypatch):
    order_id, buyer_id, _ = await create_order(test_db, status=OrderStatus.DELIVERED)
    called = False

    async def fake_unreserve(self, order_id, items):
        nonlocal called
        called = True

    monkeypatch.setattr(B2BInventoryClient, "unreserve", fake_unreserve)

    response = await async_client.post(
        f"/api/v1/orders/{order_id}/cancel",
        headers={"Authorization": f"Bearer {create_jwt_token(buyer_id)}"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "code": "CANCEL_NOT_ALLOWED",
        "message": "Отмена невозможна: заказ в статусе DELIVERED",
        "current_status": "DELIVERED",
    }
    assert called is False


@pytest.mark.asyncio
async def test_other_user_order_returns_404(async_client, test_db, monkeypatch):
    order_id, _, _ = await create_order(test_db, status=OrderStatus.PAID)
    other_buyer_id = uuid4()
    called = False

    async def fake_unreserve(self, order_id, items):
        nonlocal called
        called = True

    monkeypatch.setattr(B2BInventoryClient, "unreserve", fake_unreserve)

    response = await async_client.post(
        f"/api/v1/orders/{order_id}/cancel",
        headers={"Authorization": f"Bearer {create_jwt_token(other_buyer_id)}"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "code": "ORDER_NOT_FOUND",
        "message": "Заказ не найден",
    }
    assert called is False
