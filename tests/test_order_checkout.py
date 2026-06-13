from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from src.models import Order
from src.services.b2b_catalog_client import B2BCatalogClient, B2BSkuData
from src.services.b2b_inventory_client import B2BInventoryClient, B2BUnavailableError, ReserveFailedError
from tests.conftest import create_jwt_token


PRODUCT_ID = uuid4()
SKU_ID = uuid4()
OTHER_SKU_ID = uuid4()


def sku_data(
    sku_id: UUID = SKU_ID,
    quantity: int = 10,
    unit_price: int = 100,
    status: str = "MODERATED",
) -> B2BSkuData:
    return B2BSkuData(
        sku_id=sku_id,
        product_id=PRODUCT_ID,
        name="256GB Black",
        sku_code="SKU-1",
        unit_price=unit_price,
        available_quantity=quantity,
        product_status=status,
        product_deleted=False,
        product_blocked=False,
        image={"url": "https://example.com/image.jpg", "ordering": 0, "is_main": True},
        product_title="iPhone 15 Pro Max",
    )


@pytest.mark.asyncio
async def test_checkout_creates_paid_order_with_fixed_prices(async_client, test_db, monkeypatch):
    buyer_id = uuid4()
    idempotency_key = uuid4()
    reserve_calls = []

    async def fake_get_skus(self, sku_ids):
        return {sku_id: sku_data(sku_id=sku_id, unit_price=12999000) for sku_id in sku_ids}

    async def fake_reserve(self, idempotency_key, items):
        reserve_calls.append({"idempotency_key": idempotency_key, "items": items})

    monkeypatch.setattr(B2BCatalogClient, "get_skus", fake_get_skus)
    monkeypatch.setattr(B2BInventoryClient, "reserve", fake_reserve)

    response = await async_client.post(
        "/api/v1/orders",
        headers={
            "Authorization": f"Bearer {create_jwt_token(buyer_id)}",
            "Idempotency-Key": str(idempotency_key),
        },
        json={
            "items_snapshot": [
                {"sku_id": str(SKU_ID), "quantity": 2, "unit_price": 1},
            ],
            "comment": "test checkout",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["buyer_id"] == str(buyer_id)
    assert body["status"] == "PAID"
    assert body["items"][0]["sku_id"] == str(SKU_ID)
    assert body["items"][0]["name"] == "iPhone 15 Pro Max"
    assert body["items"][0]["unit_price"] == 12999000
    assert body["items"][0]["line_total"] == 25998000
    assert body["subtotal"] == 25998000
    assert body["total"] == 25998000
    assert reserve_calls == [
        {
            "idempotency_key": idempotency_key,
            "items": [{"sku_id": str(SKU_ID), "quantity": 2}],
        }
    ]


@pytest.mark.asyncio
async def test_partial_reserve_failure_returns_409(async_client, test_db, monkeypatch):
    buyer_id = uuid4()
    idempotency_key = uuid4()
    failed_items = [
        {
            "sku_id": str(SKU_ID),
            "requested": 2,
            "available": 1,
            "reason": "INSUFFICIENT_STOCK",
        }
    ]

    async def fake_get_skus(self, sku_ids):
        return {sku_id: sku_data(sku_id=sku_id, quantity=10) for sku_id in sku_ids}

    async def fake_reserve(self, idempotency_key, items):
        raise ReserveFailedError(failed_items)

    monkeypatch.setattr(B2BCatalogClient, "get_skus", fake_get_skus)
    monkeypatch.setattr(B2BInventoryClient, "reserve", fake_reserve)

    response = await async_client.post(
        "/api/v1/orders",
        headers={
            "Authorization": f"Bearer {create_jwt_token(buyer_id)}",
            "Idempotency-Key": str(idempotency_key),
        },
        json={"items_snapshot": [{"sku_id": str(SKU_ID), "quantity": 2}]},
    )

    assert response.status_code == 409
    assert response.json() == {
        "code": "RESERVE_FAILED",
        "message": "Не удалось зарезервировать товары",
        "failed_items": failed_items,
    }
    orders = (await test_db.execute(select(Order))).scalars().all()
    assert orders == []


@pytest.mark.asyncio
async def test_idempotency_returns_existing_order(async_client, test_db, monkeypatch):
    buyer_id = uuid4()
    idempotency_key = uuid4()
    reserve_calls = 0

    async def fake_get_skus(self, sku_ids):
        return {sku_id: sku_data(sku_id=sku_id, unit_price=500) for sku_id in sku_ids}

    async def fake_reserve(self, idempotency_key, items):
        nonlocal reserve_calls
        reserve_calls += 1

    monkeypatch.setattr(B2BCatalogClient, "get_skus", fake_get_skus)
    monkeypatch.setattr(B2BInventoryClient, "reserve", fake_reserve)

    request = {
        "items_snapshot": [{"sku_id": str(SKU_ID), "quantity": 3}],
        "comment": "same body",
    }
    headers = {
        "Authorization": f"Bearer {create_jwt_token(buyer_id)}",
        "Idempotency-Key": str(idempotency_key),
    }

    first = await async_client.post("/api/v1/orders", headers=headers, json=request)
    second = await async_client.post("/api/v1/orders", headers=headers, json=request)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["items"][0]["unit_price"] == 500
    assert reserve_calls == 1


@pytest.mark.asyncio
async def test_b2b_unavailable_returns_503(async_client, test_db, monkeypatch):
    buyer_id = uuid4()
    idempotency_key = uuid4()

    async def fake_get_skus(self, sku_ids):
        raise B2BUnavailableError("B2B down")

    async def fake_reserve(self, idempotency_key, items):
        raise AssertionError("reserve must not be called when catalog is unavailable")

    monkeypatch.setattr(B2BCatalogClient, "get_skus", fake_get_skus)
    monkeypatch.setattr(B2BInventoryClient, "reserve", fake_reserve)

    response = await async_client.post(
        "/api/v1/orders",
        headers={
            "Authorization": f"Bearer {create_jwt_token(buyer_id)}",
            "Idempotency-Key": str(idempotency_key),
        },
        json={"items_snapshot": [{"sku_id": str(SKU_ID), "quantity": 1}]},
    )

    assert response.status_code == 503
    assert response.json() == {
        "code": "B2B_UNAVAILABLE",
        "message": "Сервис товаров временно недоступен, попробуйте позже",
    }
