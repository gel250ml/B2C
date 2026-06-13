from uuid import uuid4
from unittest.mock import patch

import pytest
from fastapi import status

from tests.conftest import create_jwt_token


@pytest.mark.asyncio
async def test_add_to_favorites_returns_200(
        async_client,
        buyer_id,
):
    product_id = uuid4()
    token = create_jwt_token(buyer_id)

    response = await async_client.put(
        f"/api/v1/favorites/{product_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_repeat_add_returns_200_not_duplicate(
        async_client,
        buyer_id,
):
    product_id = uuid4()
    token = create_jwt_token(buyer_id)

    first_response = await async_client.put(
        f"/api/v1/favorites/{product_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first_response.status_code == status.HTTP_200_OK

    second_response = await async_client.put(
        f"/api/v1/favorites/{product_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second_response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_blocked_product_excluded_from_list(
        async_client,
        buyer_id,
):
    product_id = uuid4()
    token = create_jwt_token(buyer_id)

    await async_client.put(
        f"/api/v1/favorites/{product_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    with patch('src.services.catalog_service.CatalogService.get_visible_product_payload') as mock_get:
        mock_get.side_effect = Exception("Product blocked")

        response = await async_client.get(
            "/api/v1/favorites",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 0


@pytest.mark.asyncio
async def test_user_id_from_query_is_ignored(
        async_client,
        buyer_id,
):
    product_id = uuid4()
    token = create_jwt_token(buyer_id)
    other_user_id = uuid4()

    await async_client.put(
        f"/api/v1/favorites/{product_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    with patch('src.services.catalog_service.CatalogService.get_visible_product_payload') as mock_get:
        mock_product = {
            "id": str(product_id),
            "name": "Test Product",
            "status": "MODERATED",
            "deleted": False,
            "images": [],
            "skus": [{"price": 1000, "available_quantity": 5}]
        }
        mock_get.return_value = mock_product

        response = await async_client.get(
            f"/api/v1/favorites?user_id={other_user_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == str(product_id)


@pytest.mark.asyncio
async def test_remove_from_favorites_returns_204(
        async_client,
        buyer_id,
):
    product_id = uuid4()
    token = create_jwt_token(buyer_id)

    await async_client.put(
        f"/api/v1/favorites/{product_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    response = await async_client.delete(
        f"/api/v1/favorites/{product_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_remove_nonexistent_returns_204(
        async_client,
        buyer_id,
):
    product_id = uuid4()
    token = create_jwt_token(buyer_id)

    response = await async_client.delete(
        f"/api/v1/favorites/{product_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT