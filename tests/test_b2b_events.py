from uuid import uuid4
import pytest
from sqlalchemy import select
from src.models.b2b_event import B2BEvent
from src.models.cart import Cart
from src.models.cart_item import CartItem
from src.core.config import MOD_TO_B2B_KEY, B2B_TO_MOD_KEY

SERVICE_HEADERS = {
    "X-Service-Key": MOD_TO_B2B_KEY or B2B_TO_MOD_KEY,
}

@pytest.mark.asyncio
async def test_product_blocked_marks_cart_items_unavailable(
    async_client,
    test_db,
):
    sku_id = uuid4()

    cart = Cart(
        session_id=uuid4(),
    )

    test_db.add(cart)
    await test_db.flush()

    item1 = CartItem(
        cart_id=cart.id,
        sku_id=sku_id,
        quantity=1,
        unit_price_at_add=100,
    )

    item2 = CartItem(
        cart_id=cart.id,
        sku_id=sku_id,
        quantity=2,
        unit_price_at_add=100,
    )

    test_db.add_all([item1, item2])
    await test_db.commit()

    response = await async_client.post(
        "/api/v1/events/product",
        json={
            "idempotency_key": str(uuid4()),
            "event": "PRODUCT_BLOCKED",
            "product_id": str(uuid4()),
            "sku_ids": [str(sku_id)],
            "reason": "moderation",
            "date": "2026-06-01T12:00:00Z",
        },
        headers=SERVICE_HEADERS,
    )

    assert response.status_code == 202

    await test_db.refresh(item1)
    await test_db.refresh(item2)

    assert item1.unavailable_reason == "PRODUCT_BLOCKED"
    assert item2.unavailable_reason == "PRODUCT_BLOCKED"


@pytest.mark.asyncio
async def test_event_saved_in_b2b_events(
    async_client,
    test_db,
):
    sku_id = uuid4()
    event_key = uuid4()

    response = await async_client.post(
        "/api/v1/events/product",
        json={
            "idempotency_key": str(event_key),
            "event": "PRODUCT_BLOCKED",
            "product_id": str(uuid4()),
            "sku_ids": [str(sku_id)],
            "reason": "moderation",
            "date": "2026-06-01T12:00:00Z",
        },
        headers=SERVICE_HEADERS,
    )

    assert response.status_code == 202

    result = await test_db.execute(
        select(B2BEvent)
    )

    events = result.scalars().all()

    assert len(events) == 1
    assert events[0].idempotency_key == event_key


@pytest.mark.asyncio
async def test_idempotent_event_no_duplicates(
    async_client,
    test_db,
):
    payload = {
        "idempotency_key": str(uuid4()),
        "event": "PRODUCT_BLOCKED",
        "product_id": str(uuid4()),
        "sku_ids": [str(uuid4())],
        "reason": "moderation",
        "date": "2026-06-01T12:00:00Z",
    }

    first = await async_client.post(
        "/api/v1/events/product",
        json=payload,
        headers=SERVICE_HEADERS,
    )

    second = await async_client.post(
        "/api/v1/events/product",
        json=payload,
        headers=SERVICE_HEADERS,
    )

    response = await async_client.post(
        "/api/v1/events/product",
        json=payload,
        headers=SERVICE_HEADERS,
    )

    print(response.status_code)
    print(response.json())
    assert first.status_code == 202

    result = await test_db.execute(
        select(B2BEvent)
    )

    events = result.scalars().all()

    assert len(events) == 1


@pytest.mark.asyncio
async def test_missing_service_key_returns_401(
    async_client,
):
    response = await async_client.post(
        "/api/v1/events/product",
        json={
            "idempotency_key": str(uuid4()),
            "event": "PRODUCT_BLOCKED",
            "product_id": str(uuid4()),
            "sku_ids": [str(uuid4())],
            "reason": "moderation",
            "date": "2026-06-01T12:00:00Z",
        },
        headers={},
    )

    assert response.status_code == 401