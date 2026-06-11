from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from types import SimpleNamespace

from src.database.dependencies import get_db
from src.main import app


class MockB2BClient:
    response_payload = None
    status_code = 200
    requested_url = None
    requested_headers = None

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url: str, headers=None):
        MockB2BClient.requested_url = url
        MockB2BClient.requested_headers = headers or {}
        return httpx.Response(
            status_code=MockB2BClient.status_code,
            json=MockB2BClient.response_payload,
            request=httpx.Request("GET", f"http://b2b.test{url}"),
        )


@pytest.fixture(autouse=True)
def mock_b2b_client(monkeypatch):
    MockB2BClient.response_payload = None
    MockB2BClient.status_code = 200
    MockB2BClient.requested_url = None
    MockB2BClient.requested_headers = None
    monkeypatch.setattr("src.services.catalog_service.httpx", SimpleNamespace(AsyncClient=MockB2BClient))


@pytest_asyncio.fixture
async def async_client():
    async def override_get_db():
        yield None

    app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()


def build_product_payload(product_id: str, status: str = "MODERATED", deleted: bool = False):
    return {
        "id": product_id,
        "slug": "iphone-15-pro-max",
        "title": "iPhone 15 Pro Max",
        "description": "Флагманский смартфон Apple 2024 года с чипом A17 Pro",
        "images": [
            {"url": "https://cdn.example.com/iphone-front.jpg", "ordering": 0},
            {"url": "https://cdn.example.com/iphone-back.jpg", "ordering": 1},
        ],
        "status": status,
        "deleted": deleted,
        "characteristics": [
            {"name": "Бренд", "value": "Apple"},
            {"name": "Страна-производитель", "value": "Китай"},
        ],
        "skus": [
            {
                "id": str(uuid4()),
                "name": "256GB Black",
                "price": 12999000,
                "discount": 0,
                "image": "/s3/iphone15-black-256.jpg",
                "active_quantity": 10,
                "reserved_quantity": 2,
                "cost_price": 9000000,
                "characteristics": [
                    {"name": "Цвет", "value": "Чёрный"},
                    {"name": "Объём памяти", "value": "256 ГБ"},
                ],
            },
            {
                "id": str(uuid4()),
                "name": "256GB White",
                "price": 12999000,
                "discount": 500000,
                "image": "/s3/iphone15-white-256.jpg",
                "active_quantity": 0,
                "reserved_quantity": 1,
                "cost_price": 9100000,
                "characteristics": [
                    {"name": "Цвет", "value": "Белый"},
                    {"name": "Объём памяти", "value": "256 ГБ"},
                ],
            },
        ],
    }


@pytest.mark.asyncio
async def test_product_card_returns_full_data_with_skus(async_client):
    product_id = uuid4()
    MockB2BClient.response_payload = build_product_payload(str(product_id))

    response = await async_client.get(f"/api/v1/catalog/products/{product_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(product_id)
    assert data["slug"] == "iphone-15-pro-max"
    assert data["title"] == "iPhone 15 Pro Max"
    assert data["description"]
    assert len(data["images"]) == 2
    assert data["characteristics"][0] == {"name": "Бренд", "value": "Apple"}
    assert len(data["skus"]) == 2
    assert data["skus"][0]["price"] == 12999000
    assert data["skus"][1]["discount"] == 500000
    assert MockB2BClient.requested_url == f"/api/v1/products/{product_id}"


@pytest.mark.asyncio
async def test_cost_price_absent_in_response(async_client):
    product_id = uuid4()
    MockB2BClient.response_payload = build_product_payload(str(product_id))

    response = await async_client.get(f"/api/v1/catalog/products/{product_id}")

    assert response.status_code == 200
    sku = response.json()["skus"][0]
    assert "cost_price" not in sku
    assert "reserved_quantity" not in sku


@pytest.mark.asyncio
async def test_blocked_product_returns_404(async_client):
    product_id = uuid4()
    MockB2BClient.response_payload = build_product_payload(str(product_id), status="BLOCKED")

    response = await async_client.get(f"/api/v1/catalog/products/{product_id}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_sku_without_stock_is_shown_as_unavailable(async_client):
    product_id = uuid4()
    MockB2BClient.response_payload = build_product_payload(str(product_id))

    response = await async_client.get(f"/api/v1/catalog/products/{product_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["skus"][1]["active_quantity"] == 0
    assert data["skus"][1]["in_stock"] is False
    assert data["skus"][0]["in_stock"] is True
