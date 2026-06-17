from uuid import UUID, uuid4

import pytest

from src.services.b2b_catalog_client import B2BCatalogClient, B2BSkuData
from tests.conftest import create_jwt_token


PRODUCT_ID = uuid4()
SKU_ID = uuid4()
OTHER_SKU_ID = uuid4()


def sku_data(sku_id: UUID = SKU_ID, quantity: int = 10, status: str = "MODERATED") -> B2BSkuData:
    return B2BSkuData(
        sku_id=sku_id,
        product_id=PRODUCT_ID,
        name="Test SKU",
        sku_code="SKU-1",
        unit_price=100,
        available_quantity=quantity,
        product_status=status,
        product_deleted=False,
        product_blocked=False,
        image={"url": "https://example.com/image.jpg", "ordering": 0, "is_main": True},
    )


@pytest.mark.asyncio
async def test_add_sku_increments_quantity_if_already_in_cart(async_client, monkeypatch):
    async def fake_get_skus(self, product_ids):
        return {SKU_ID: sku_data(SKU_ID)}

    monkeypatch.setattr(B2BCatalogClient, "get_skus", fake_get_skus)
    session_id = str(uuid4())

    first = await async_client.post(
        "/api/v1/cart/items",
        headers={"X-Session-Id": session_id},
        json={"sku_id": str(SKU_ID), "quantity": 2},
    )
    second = await async_client.post(
        "/api/v1/cart/items",
        headers={"X-Session-Id": session_id},
        json={"sku_id": str(SKU_ID), "quantity": 3},
    )

    assert first.status_code == 201
    assert second.status_code == 200
    body = second.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 5


@pytest.mark.asyncio
async def test_get_cart_enriched_with_b2b_data(async_client, monkeypatch):
    requested_batches = []

    async def fake_get_skus(self, product_ids):
        requested_batches.append(list(product_ids))
        return {SKU_ID: sku_data(SKU_ID)}

    monkeypatch.setattr(B2BCatalogClient, "get_skus", fake_get_skus)
    session_id = str(uuid4())

    await async_client.post(
        "/api/v1/cart/items",
        headers={"X-Session-Id": session_id},
        json={"sku_id": str(SKU_ID), "quantity": 2},
    )
    response = await async_client.get("/api/v1/cart", headers={"X-Session-Id": session_id})

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["name"] == "Test SKU"
    assert body["items"][0]["unit_price"] == 100
    assert body["items"][0]["line_total"] == 200
    assert body["subtotal"] == 200
    assert requested_batches[-1] == [PRODUCT_ID]


@pytest.mark.asyncio
async def test_unavailable_sku_shown_with_reason(async_client, monkeypatch):
    current_quantity = 10

    async def fake_get_skus(self, product_ids):
        return {SKU_ID: sku_data(SKU_ID, quantity=current_quantity)}

    monkeypatch.setattr(B2BCatalogClient, "get_skus", fake_get_skus)
    session_id = str(uuid4())

    await async_client.post(
        "/api/v1/cart/items",
        headers={"X-Session-Id": session_id},
        json={"sku_id": str(SKU_ID), "quantity": 2},
    )
    current_quantity = 0

    response = await async_client.get("/api/v1/cart", headers={"X-Session-Id": session_id})

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["is_available"] is False
    assert body["items"][0]["unavailable_reason"] == "OUT_OF_STOCK"
    assert body["items"][0]["line_total"] == 0
    assert body["subtotal"] == 0
    assert body["is_valid"] is False


@pytest.mark.asyncio
async def test_guest_cart_merged_on_login(async_client, monkeypatch):
    async def fake_get_skus(self, product_ids):
        return {SKU_ID: sku_data(SKU_ID)}

    monkeypatch.setattr(B2BCatalogClient, "get_skus", fake_get_skus)
    session_id = str(uuid4())
    user_id = uuid4()
    token = create_jwt_token(user_id)

    await async_client.post(
        "/api/v1/cart/items",
        headers={"X-Session-Id": session_id},
        json={"sku_id": str(SKU_ID), "quantity": 5},
    )
    await async_client.post(
        "/api/v1/cart/items",
        headers={"Authorization": f"Bearer {token}"},
        json={"sku_id": str(SKU_ID), "quantity": 2},
    )

    response = await async_client.post(
        "/api/v1/cart/merge",
        headers={"Authorization": f"Bearer {token}", "X-Session-Id": session_id},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["sku_id"] == str(SKU_ID)
    assert body["items"][0]["quantity"] == 5

    guest_response = await async_client.get("/api/v1/cart", headers={"X-Session-Id": session_id})
    assert guest_response.status_code == 200
    assert guest_response.json()["items"] == []
