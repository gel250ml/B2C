from uuid import uuid4

import pytest
from sqlalchemy import select

from src.core.config import MOD_TO_B2B_KEY, B2B_TO_MOD_KEY
from src.models import (
    Address,
    B2BEvent,
    Buyer,
    Cart,
    CartItem,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    PaymentMethodType,
)

SERVICE_HEADERS = {
    "X-Service-Key": MOD_TO_B2B_KEY or B2B_TO_MOD_KEY,
}
EVENT_URL = "/api/v1/b2b/events"


def product_blocked_payload(sku_id, *, idempotency_key=None, product_id=None):
    return {
        "event_type": "PRODUCT_BLOCKED",
        "idempotency_key": str(idempotency_key or uuid4()),
        "occurred_at": "2026-06-01T12:00:00Z",
        "payload": {
            "product_id": str(product_id or uuid4()),
            "sku_ids": [str(sku_id)],
            "reason": "moderation",
        },
    }


@pytest.mark.asyncio
async def test_product_blocked_marks_cart_items_unavailable(
    async_client,
    test_db,
):
    sku_id = uuid4()
    product_id = uuid4()

    cart = Cart(session_id=uuid4())
    test_db.add(cart)
    await test_db.flush()

    item1 = CartItem(
        cart_id=cart.id,
        product_id=product_id,
        sku_id=sku_id,
        quantity=1,
        unit_price_at_add=100,
    )
    item2 = CartItem(
        cart_id=cart.id,
        product_id=product_id,
        sku_id=sku_id,
        quantity=2,
        unit_price_at_add=100,
    )

    test_db.add_all([item1, item2])
    await test_db.commit()

    response = await async_client.post(
        EVENT_URL,
        json=product_blocked_payload(sku_id, product_id=product_id),
        headers=SERVICE_HEADERS,
    )

    assert response.status_code == 202

    await test_db.refresh(item1)
    await test_db.refresh(item2)

    assert item1.unavailable_reason == "PRODUCT_BLOCKED"
    assert item2.unavailable_reason == "PRODUCT_BLOCKED"


@pytest.mark.asyncio
async def test_orders_not_affected_by_product_blocked(
    async_client,
    test_db,
):
    buyer = Buyer(
        email=f"{uuid4()}@example.com",
        password_hash="hash",
        first_name="Test",
    )
    test_db.add(buyer)
    await test_db.flush()

    address = Address(
        buyer_id=buyer.id,
        country="RU",
        city="Moscow",
        street="Tverskaya",
        building="1",
    )
    payment_method = PaymentMethod(
        buyer_id=buyer.id,
        type=PaymentMethodType.CARD,
        card_last4="1234",
        card_brand="VISA",
    )
    test_db.add_all([address, payment_method])
    await test_db.flush()

    sku_id = uuid4()
    product_id = uuid4()
    order = Order(
        buyer_id=buyer.id,
        address_id=address.id,
        payment_method_id=payment_method.id,
        number="ORD-1",
        status=OrderStatus.PAID,
        subtotal=100,
        delivery_cost=0,
        total=100,
        idempotency_key=uuid4(),
    )
    test_db.add(order)
    await test_db.flush()

    order_item = OrderItem(
        order_id=order.id,
        product_id=product_id,
        sku_id=sku_id,
        name="Product",
        product_title="Product",
        sku_name="SKU",
        quantity=1,
        unit_price=100,
        line_total=100,
    )
    test_db.add(order_item)
    await test_db.commit()

    response = await async_client.post(
        EVENT_URL,
        json=product_blocked_payload(sku_id, product_id=product_id),
        headers=SERVICE_HEADERS,
    )

    assert response.status_code == 202

    await test_db.refresh(order)
    await test_db.refresh(order_item)

    assert order.status == OrderStatus.PAID
    assert order_item.unit_price == 100
    assert order_item.line_total == 100


@pytest.mark.asyncio
async def test_event_saved_in_b2b_events(
    async_client,
    test_db,
):
    sku_id = uuid4()
    event_key = uuid4()

    response = await async_client.post(
        EVENT_URL,
        json=product_blocked_payload(sku_id, idempotency_key=event_key),
        headers=SERVICE_HEADERS,
    )

    assert response.status_code == 202

    result = await test_db.execute(select(B2BEvent))
    events = result.scalars().all()

    assert len(events) == 1
    assert events[0].idempotency_key == event_key
    assert events[0].event_type == "PRODUCT_BLOCKED"
    assert events[0].payload["sku_ids"] == [str(sku_id)]


@pytest.mark.asyncio
async def test_idempotent_event_no_side_effects(
    async_client,
    test_db,
):
    sku_id = uuid4()
    product_id = uuid4()
    event_key = uuid4()

    cart = Cart(session_id=uuid4())
    test_db.add(cart)
    await test_db.flush()

    item = CartItem(
        cart_id=cart.id,
        product_id=product_id,
        sku_id=sku_id,
        quantity=1,
        unit_price_at_add=100,
    )
    test_db.add(item)
    await test_db.commit()

    payload = product_blocked_payload(
        sku_id,
        idempotency_key=event_key,
        product_id=product_id,
    )

    first = await async_client.post(EVENT_URL, json=payload, headers=SERVICE_HEADERS)
    await test_db.refresh(item)
    item.unavailable_reason = None
    await test_db.commit()

    second = await async_client.post(EVENT_URL, json=payload, headers=SERVICE_HEADERS)
    await test_db.refresh(item)

    assert first.status_code == 202
    assert second.status_code == 202
    assert item.unavailable_reason is None

    result = await test_db.execute(select(B2BEvent))
    events = result.scalars().all()
    assert len(events) == 1


@pytest.mark.asyncio
async def test_sku_out_of_stock_marks_cart_items_out_of_stock(
    async_client,
    test_db,
):
    sku_id = uuid4()

    cart = Cart(session_id=uuid4())
    test_db.add(cart)
    await test_db.flush()

    item = CartItem(
        cart_id=cart.id,
        sku_id=sku_id,
        quantity=1,
        unit_price_at_add=100,
    )
    test_db.add(item)
    await test_db.commit()

    response = await async_client.post(
        EVENT_URL,
        json={
            "event_type": "SKU_OUT_OF_STOCK",
            "idempotency_key": str(uuid4()),
            "occurred_at": "2026-06-01T12:00:00Z",
            "payload": {
                "sku_id": str(sku_id),
                "product_id": str(uuid4()),
                "available_quantity": 0,
                "quantity": 0,
            },
        },
        headers=SERVICE_HEADERS,
    )

    assert response.status_code == 202

    await test_db.refresh(item)
    assert item.unavailable_reason == "OUT_OF_STOCK"


@pytest.mark.asyncio
async def test_product_hard_blocked_marks_cart_items_unavailable(
    async_client,
    test_db,
):
    sku_id = uuid4()
    product_id = uuid4()

    cart = Cart(session_id=uuid4())
    test_db.add(cart)
    await test_db.flush()

    item = CartItem(
        cart_id=cart.id,
        product_id=product_id,
        sku_id=sku_id,
        quantity=1,
        unit_price_at_add=100,
    )
    test_db.add(item)
    await test_db.commit()

    response = await async_client.post(
        EVENT_URL,
        json={
            "event_type": "PRODUCT_HARD_BLOCKED",
            "idempotency_key": str(uuid4()),
            "occurred_at": "2026-06-01T12:00:00Z",
            "payload": {
                "product_id": str(product_id),
                "sku_ids": [str(sku_id)],
                "reason": "hard moderation block",
            },
        },
        headers=SERVICE_HEADERS,
    )

    assert response.status_code == 202

    await test_db.refresh(item)
    assert item.unavailable_reason == "PRODUCT_BLOCKED"


@pytest.mark.asyncio
async def test_sku_back_in_stock_clears_only_out_of_stock_reason(
    async_client,
    test_db,
):
    sku_id = uuid4()
    product_id = uuid4()

    cart = Cart(session_id=uuid4())
    test_db.add(cart)
    await test_db.flush()

    out_of_stock_item = CartItem(
        cart_id=cart.id,
        product_id=product_id,
        sku_id=sku_id,
        quantity=1,
        unit_price_at_add=100,
        unavailable_reason="OUT_OF_STOCK",
    )
    blocked_item = CartItem(
        cart_id=cart.id,
        product_id=product_id,
        sku_id=sku_id,
        quantity=1,
        unit_price_at_add=100,
        unavailable_reason="PRODUCT_BLOCKED",
    )
    test_db.add_all([out_of_stock_item, blocked_item])
    await test_db.commit()

    response = await async_client.post(
        EVENT_URL,
        json={
            "event_type": "SKU_BACK_IN_STOCK",
            "idempotency_key": str(uuid4()),
            "occurred_at": "2026-06-01T12:00:00Z",
            "payload": {
                "sku_id": str(sku_id),
                "product_id": str(product_id),
                "available_quantity": 5,
            },
        },
        headers=SERVICE_HEADERS,
    )

    assert response.status_code == 202

    await test_db.refresh(out_of_stock_item)
    await test_db.refresh(blocked_item)
    assert out_of_stock_item.unavailable_reason is None
    assert blocked_item.unavailable_reason == "PRODUCT_BLOCKED"


@pytest.mark.asyncio
async def test_missing_service_key_returns_401(
    async_client,
):
    response = await async_client.post(
        EVENT_URL,
        json=product_blocked_payload(uuid4()),
        headers={},
    )

    assert response.status_code == 401
