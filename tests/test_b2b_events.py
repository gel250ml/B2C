from datetime import datetime
from uuid import uuid4

import pytest

from src.database.dependencies import verify_moderation_service_key
from src.main import app


def event_payload() -> dict:
    return {
        "event_type": "PRODUCT_DELETED",
        "idempotency_key": str(uuid4()),
        "payload": {"product_id": str(uuid4())},
        "occurred_at": datetime.utcnow().isoformat(),
    }


@pytest.mark.asyncio
async def test_b2b_event_requires_service_key(async_client):
    response = await async_client.post("/api/v1/b2b/events", json=event_payload())

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_b2b_event_accepted_with_service_key(async_client):
    async def allow_service_key():
        return None

    app.dependency_overrides[verify_moderation_service_key] = allow_service_key

    response = await async_client.post("/api/v1/b2b/events", json=event_payload())

    assert response.status_code == 202
    assert response.json() == {"ok": True, "processed": False}
