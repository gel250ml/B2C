from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from src.models import Collection, CollectionProduct
from src.services.b2b_catalog_client import B2BCatalogClient


def _collection(
    *,
    title: str = "Hits",
    priority: int = 1,
    is_active: bool = True,
    start_date=None,
) -> Collection:
    return Collection(
        title=title,
        description="Top products",
        cover_image_url="https://cdn.example.test/collection.jpg",
        target_url="https://example.test/catalog/hits",
        priority=priority,
        is_active=is_active,
        start_date=start_date,
    )


def _product(product_id: UUID, *, name: str = "Phone", status: str = "MODERATED") -> dict:
    return {
        "id": str(product_id),
        "name": name,
        "slug": name.lower(),
        "status": status,
        "min_price": 1000,
        "has_stock": True,
        "images": [
            {
                "id": str(uuid4()),
                "url": "https://cdn.example.test/product.jpg",
                "ordering": 0,
                "is_main": True,
            }
        ],
    }


@pytest.mark.asyncio
async def test_collections_list_returns_metadata_without_products(async_client, test_db):
    today = datetime.now(UTC).date()
    first = _collection(title="New", priority=1, start_date=today - timedelta(days=1))
    second = _collection(title="Hits", priority=2, start_date=today)
    inactive = _collection(title="Hidden", priority=0, is_active=False)
    future = _collection(title="Future", priority=0, start_date=today + timedelta(days=1))
    test_db.add_all([second, first, inactive, future])
    await test_db.commit()

    response = await async_client.get("/api/v1/main/collections?limit=10&offset=0")

    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"] == {"total_count": 2, "limit": 10, "offset": 0}
    assert [item["id"] for item in payload["collections"]] == [str(first.id), str(second.id)]
    assert "products" not in payload["collections"][0]


@pytest.mark.asyncio
async def test_collection_products_enriched_from_b2b(async_client, test_db, monkeypatch):
    collection = _collection()
    first_product_id = uuid4()
    second_product_id = uuid4()
    test_db.add(collection)
    await test_db.flush()
    test_db.add_all(
        [
            CollectionProduct(collection_id=collection.id, product_id=first_product_id, ordering=1),
            CollectionProduct(collection_id=collection.id, product_id=second_product_id, ordering=2),
        ]
    )
    await test_db.commit()

    async def fake_get_products_by_ids(self, product_ids):
        assert product_ids == [first_product_id, second_product_id]
        return [_product(second_product_id, name="Laptop"), _product(first_product_id, name="Phone")]

    monkeypatch.setattr(B2BCatalogClient, "get_products_by_ids", fake_get_products_by_ids)

    response = await async_client.get(f"/api/v1/collections/{collection.id}/products")

    assert response.status_code == 200
    payload = response.json()
    assert payload["collection_id"] == str(collection.id)
    assert payload["collection_title"] == "Hits"
    assert [item["id"] for item in payload["items"]] == [str(first_product_id), str(second_product_id)]
    assert [item["name"] for item in payload["items"]] == ["Phone", "Laptop"]
    assert payload["unavailable_ids"] == []


@pytest.mark.asyncio
async def test_unavailable_products_in_unavailable_ids(async_client, test_db, monkeypatch):
    collection = _collection()
    deleted_product_id = uuid4()
    missing_product_id = uuid4()
    test_db.add(collection)
    await test_db.flush()
    test_db.add_all(
        [
            CollectionProduct(collection_id=collection.id, product_id=deleted_product_id, ordering=1),
            CollectionProduct(collection_id=collection.id, product_id=missing_product_id, ordering=2),
        ]
    )
    await test_db.commit()
    deleted_product = _product(deleted_product_id, name="Blocked")
    deleted_product["deleted"] = True

    async def fake_get_products_by_ids(self, product_ids):
        return [deleted_product]

    monkeypatch.setattr(B2BCatalogClient, "get_products_by_ids", fake_get_products_by_ids)

    response = await async_client.get(f"/api/v1/collections/{collection.id}/products")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["unavailable_ids"] == [str(deleted_product_id), str(missing_product_id)]


@pytest.mark.asyncio
async def test_unknown_collection_returns_404(async_client):
    response = await async_client.get(f"/api/v1/collections/{uuid4()}/products")

    assert response.status_code == 404
    assert response.json() == {"message": "Collection not found", "code": "NOT_FOUND"}
