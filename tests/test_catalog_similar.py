from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio

from src.database.dependencies import get_db
from src.main import app


class MockB2BClient:
    responses: dict[str, tuple[int, dict]] = {}
    requested_urls: list[str] = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url: str, headers=None):
        MockB2BClient.requested_urls.append(url)
        status_code, payload = MockB2BClient.responses.get(url, (404, {"code": "NOT_FOUND", "message": "Not found"}))
        return httpx.Response(
            status_code=status_code,
            json=payload,
            request=httpx.Request("GET", f"http://b2b.test{url}"),
        )


@pytest.fixture(autouse=True)
def mock_b2b_client(monkeypatch):
    MockB2BClient.responses = {}
    MockB2BClient.requested_urls = []
    monkeypatch.setattr(
        "src.services.catalog_service.httpx",
        SimpleNamespace(AsyncClient=MockB2BClient, HTTPError=httpx.HTTPError),
    )


@pytest_asyncio.fixture
async def async_client():
    async def override_get_db():
        yield None

    app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()


def make_product(product_id: str, category_id: str) -> dict:
    return {
        "id": product_id,
        "name": "Current product",
        "status": "MODERATED",
        "deleted": False,
        "category_id": category_id,
        "skus": [{"id": str(uuid4()), "price": 1000, "active_quantity": 1}],
        "images": [{"url": "https://cdn.example.com/current.jpg", "is_main": True}],
    }


def make_similar_product(index: int, product_id: str | None = None) -> dict:
    return {
        "id": product_id or str(uuid4()),
        "title": f"Similar product {index}",
        "price": 1000 + index,
        "in_stock": index % 2 == 0,
        "image": f"https://cdn.example.com/similar-{index}.jpg",
    }


@pytest.mark.asyncio
async def test_similar_returns_up_to_8_from_same_category(async_client):
    product_id = uuid4()
    category_id = uuid4()
    product_url = f"/api/v1/public/products/{product_id}"
    similar_url = f"/api/v1/public/products/{product_id}/similar?category={category_id}&limit=8&offset=0"
    similar_items = [make_similar_product(0, product_id=str(product_id))]
    similar_items.extend(make_similar_product(i) for i in range(1, 11))
    MockB2BClient.responses = {
        product_url: (200, make_product(str(product_id), str(category_id))),
        similar_url: (200, {"items": similar_items, "total_count": len(similar_items), "limit": 8, "offset": 0}),
    }

    response = await async_client.get(f"/api/v1/catalog/products/{product_id}/similar?limit=8")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 8
    assert str(product_id) not in {item["id"] for item in data}
    assert set(data[0].keys()) == {"id", "name", "min_price", "has_stock", "images"}
    assert data[0]["name"] == "Similar product 1"
    assert data[0]["min_price"] == 1001
    assert isinstance(data[0]["has_stock"], bool)
    assert data[0]["images"][0]["url"] == "https://cdn.example.com/similar-1.jpg"
    assert product_url in MockB2BClient.requested_urls
    assert similar_url in MockB2BClient.requested_urls


@pytest.mark.asyncio
async def test_empty_category_returns_200_empty_list(async_client):
    product_id = uuid4()
    category_id = uuid4()
    product_url = f"/api/v1/public/products/{product_id}"
    similar_url = f"/api/v1/public/products/{product_id}/similar?category={category_id}&limit=8&offset=0"
    MockB2BClient.responses = {
        product_url: (200, make_product(str(product_id), str(category_id))),
        similar_url: (200, {"items": [], "total_count": 0, "limit": 8, "offset": 0}),
    }

    response = await async_client.get(f"/api/v1/catalog/products/{product_id}/similar?limit=8")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_unknown_product_returns_404(async_client):
    product_id = uuid4()
    product_url = f"/api/v1/public/products/{product_id}"
    MockB2BClient.responses = {
        product_url: (404, {"code": "NOT_FOUND", "message": "Product not found"}),
    }

    response = await async_client.get(f"/api/v1/catalog/products/{product_id}/similar?limit=8")

    assert response.status_code == 404
    assert response.json() == {"code": "NOT_FOUND", "message": "Product not found"}
    assert MockB2BClient.requested_urls == [product_url]
