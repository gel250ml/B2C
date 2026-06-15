from uuid import uuid4
from unittest.mock import patch, AsyncMock

import pytest
from fastapi import status

from tests.conftest import create_jwt_token


@pytest.mark.asyncio
async def test_subscribe_returns_204_on_success(
        async_client,
        buyer_id,
):
    product_id = uuid4()
    token = create_jwt_token(buyer_id)

    with patch('src.services.product_subscription_service.ProductSubscriptionService.check_product_exists', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = True

        response = await async_client.post(
            f"/api/v1/favorites/{product_id}/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "events": [
                    "BACK_IN_STOCK",
                    "PRICE_DROP",
                ]
            },
        )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()

    assert data["product_id"] == str(product_id)
    assert set(data["notify_on"]) == {
        "BACK_IN_STOCK",
        "PRICE_DROP",
    }

@pytest.mark.asyncio
async def test_duplicate_subscription_returns_409(
        async_client,
        buyer_id,
):
    product_id = uuid4()
    token = create_jwt_token(buyer_id)

    payload = {
        "events": ["BACK_IN_STOCK"]
    }

    with patch('src.services.product_subscription_service.ProductSubscriptionService.check_product_exists', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = True

        first_response = await async_client.post(
            f"/api/v1/favorites/{product_id}/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        assert first_response.status_code == status.HTTP_201_CREATED

        second_response = await async_client.post(
            f"/api/v1/favorites/{product_id}/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )

        assert second_response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_invalid_notify_on_returns_400(
        async_client,
        buyer_id,
):
    product_id = uuid4()
    token = create_jwt_token(buyer_id)

    response = await async_client.post(
        f"/api/v1/favorites/{product_id}/subscribe",
        headers={"Authorization": f"Bearer {token}"},
        json={"events": []},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_subscribe_to_unknown_product_returns_404(
        async_client,
        buyer_id,
):
    unknown_product_id = uuid4()
    token = create_jwt_token(buyer_id)

    with patch('src.services.product_subscription_service.ProductSubscriptionService.check_product_exists', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = False

        response = await async_client.post(
            f"/api/v1/favorites/{unknown_product_id}/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"events": ["BACK_IN_STOCK"]},
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_unsubscribe_returns_204_on_success(
        async_client,
        buyer_id,
):
    product_id = uuid4()
    token = create_jwt_token(buyer_id)

    with patch('src.services.product_subscription_service.ProductSubscriptionService.check_product_exists', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = True

        await async_client.post(
            f"/api/v1/favorites/{product_id}/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"events": ["BACK_IN_STOCK"]},
        )

        response = await async_client.delete(
            f"/api/v1/favorites/{product_id}/subscribe",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.text == ""


@pytest.mark.asyncio
async def test_unsubscribe_from_nonexistent_returns_404(
        async_client,
        buyer_id,
):
    product_id = uuid4()
    token = create_jwt_token(buyer_id)

    response = await async_client.delete(
        f"/api/v1/favorites/{product_id}/subscribe",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND