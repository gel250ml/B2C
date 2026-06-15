from uuid import uuid4

import pytest

from src.services.catalog_service import CatalogService


ROOT_ID = uuid4()
CHILD_ID = uuid4()
LEAF_ID = uuid4()
UNKNOWN_PARENT_ID = uuid4()
PRODUCT_ID = uuid4()


def category_payload():
    return [
        {
            "id": str(ROOT_ID),
            "name": "Электроника",
            "slug": "electronics",
            "parent_id": None,
            "description": "Техника и гаджеты",
            "product_count": 10,
            "is_active": True,
        },
        {
            "id": str(CHILD_ID),
            "name": "Смартфоны",
            "slug": "smartphones",
            "parent_id": str(ROOT_ID),
            "description": "Мобильные телефоны",
            "product_count": 4,
            "is_active": True,
        },
        {
            "id": str(LEAF_ID),
            "name": "Android",
            "slug": "android",
            "parent_id": str(CHILD_ID),
            "description": "Android-смартфоны",
            "product_count": 2,
            "is_active": True,
        },
    ]


async def patch_categories(monkeypatch, payload):
    async def fake_get_b2b_json(self, path, query, not_found_message="Category not found"):
        return payload

    monkeypatch.setattr(CatalogService, "_get_b2b_json", fake_get_b2b_json)


@pytest.mark.asyncio
async def test_category_tree_returns_nested_structure(async_client, monkeypatch):
    await patch_categories(monkeypatch, category_payload())

    response = await async_client.get("/api/v1/catalog/categories/tree")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "max-age=3600"
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == str(ROOT_ID)
    assert data[0]["name"] == "Электроника"
    assert data[0]["parent_id"] is None
    assert data[0]["level"] == 0
    assert data[0]["path"] == ["Электроника"]
    assert data[0]["children"][0]["id"] == str(CHILD_ID)
    assert data[0]["children"][0]["level"] == 1
    assert data[0]["children"][0]["path"] == ["Электроника", "Смартфоны"]
    assert data[0]["children"][0]["children"][0]["id"] == str(LEAF_ID)
    assert data[0]["children"][0]["children"][0]["children"] == []


@pytest.mark.asyncio
async def test_breadcrumbs_return_path_from_root(async_client, monkeypatch):
    await patch_categories(monkeypatch, category_payload())

    response = await async_client.get(f"/api/v1/breadcrumbs?category_id={LEAF_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["meta"] == {
        "resolved_via": "category_id",
        "category_id": str(LEAF_ID),
        "product_id": None,
    }
    assert [item["id"] for item in body["data"]] == [str(ROOT_ID), str(CHILD_ID), str(LEAF_ID)]
    assert [item["name"] for item in body["data"]] == ["Электроника", "Смартфоны", "Android"]
    assert [item["level"] for item in body["data"]] == [0, 1, 2]
    assert [item["is_current"] for item in body["data"]] == [False, False, True]
    assert body["data"][-1]["url"] == "/catalog/electronics/smartphones/android"


@pytest.mark.asyncio
async def test_orphan_node_returns_422(async_client, monkeypatch):
    await patch_categories(
        monkeypatch,
        [
            {
                "id": str(LEAF_ID),
                "name": "Android",
                "slug": "android",
                "parent_id": str(UNKNOWN_PARENT_ID),
            }
        ],
    )

    response = await async_client.get("/api/v1/catalog/categories/tree")

    assert response.status_code == 422
    assert response.json() == {
        "error": "orphan_node",
        "message": "category hierarchy is broken",
    }


@pytest.mark.asyncio
async def test_ambiguous_params_returns_400(async_client):
    response = await async_client.get(
        f"/api/v1/breadcrumbs?category_id={LEAF_ID}&product_id={PRODUCT_ID}"
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": "ambiguous_param",
        "message": "only one of category_id or product_id must be provided",
    }


@pytest.mark.asyncio
async def test_unknown_category_returns_404(async_client, monkeypatch):
    await patch_categories(monkeypatch, category_payload())

    response = await async_client.get(f"/api/v1/catalog/categories/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"code": "NOT_FOUND", "message": "Category not found"}


@pytest.mark.asyncio
async def test_missing_breadcrumb_param_returns_400(async_client):
    response = await async_client.get("/api/v1/breadcrumbs")

    assert response.status_code == 400
    assert response.json() == {
        "error": "missing_param",
        "message": "category_id or product_id must be provided",
    }
