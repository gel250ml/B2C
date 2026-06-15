from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio

from src.database.dependencies import get_db
from src.main import app


class MockB2BClient:
    response_payload = None
    status_code = 200
    requested_url = None
    requested_params = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url: str, headers=None, params=None):
        MockB2BClient.requested_url = url
        MockB2BClient.requested_params = params
        return httpx.Response(
            status_code=MockB2BClient.status_code,
            json=MockB2BClient.response_payload,
            request=httpx.Request("GET", f"http://b2b.test{url}"),
        )


@pytest.fixture(autouse=True)
def mock_b2b(monkeypatch):
    MockB2BClient.response_payload = {"items": [], "total_count": 0, "limit": 20, "offset": 0}
    MockB2BClient.status_code = 200
    MockB2BClient.requested_url = None
    MockB2BClient.requested_params = None
    monkeypatch.setattr("src.services.catalog_service.httpx", SimpleNamespace(AsyncClient=MockB2BClient, HTTPError=httpx.HTTPError))


@pytest_asyncio.fixture
async def async_client():
    async def override_get_db():
        yield None

    app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()


def make_product(product_id: str | None = None) -> dict:
    pid = product_id or str(uuid4())
    return {
        "id": pid,
        "title": "Беспроводные наушники",
        "slug": "naushniki",
        "status": "MODERATED",
        "deleted": False,
        "category_id": str(uuid4()),
        "min_price": 5000,
        "images": [],
        "skus": [{"id": str(uuid4()), "price": 5000, "discount": 0, "active_quantity": 3}],
    }


@pytest.mark.asyncio
async def test_search_returns_matching_products(async_client):
    product = make_product()
    MockB2BClient.response_payload = {"items": [product], "total_count": 1, "limit": 20, "offset": 0}

    resp = await async_client.get("/api/v1/catalog/products?q=наушники")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 1
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_search_too_short_returns_400(async_client):
    resp = await async_client.get("/api/v1/catalog/products?q=аб")

    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "INVALID_REQUEST"
    assert "3 characters" in body["message"]

@pytest.mark.asyncio
async def test_search_too_long_returns_400(async_client):
    long_query = "а" * 256
    resp = await async_client.get(f"/api/v1/catalog/products?q={long_query}")

    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "INVALID_REQUEST"
    assert "255 characters" in body["message"]


@pytest.mark.asyncio
async def test_search_empty_result_returns_200(async_client):
    MockB2BClient.response_payload = {"items": [], "total_count": 0, "limit": 20, "offset": 0}

    resp = await async_client.get("/api/v1/catalog/products?q=несуществующий")

    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total_count"] == 0


@pytest.mark.asyncio
async def test_search_proxied_to_b2b_as_search_param(async_client):
    resp = await async_client.get("/api/v1/catalog/products?q=наушники")

    assert resp.status_code == 200
    assert "search=" in MockB2BClient.requested_url


@pytest.mark.asyncio
async def test_search_with_category_filter(async_client):
    category_id = str(uuid4())
    product = make_product()
    MockB2BClient.response_payload = {"items": [product], "total_count": 1, "limit": 20, "offset": 0}

    resp = await async_client.get(
        f"/api/v1/catalog/products?q=наушники&filter[category_id]={category_id}"
    )

    assert resp.status_code == 200
    assert "category_id=" in MockB2BClient.requested_url
    assert "search=" in MockB2BClient.requested_url