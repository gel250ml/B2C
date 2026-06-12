from uuid import UUID

import httpx

from src.core.config import B2B_URL, B2C_TO_B2B_KEY


class B2BUnavailableError(Exception):
    """Raised when B2B inventory service cannot complete unreserve now."""


class B2BInventoryClient:
    def __init__(self) -> None:
        self.base_url = B2B_URL
        self.headers: dict[str, str] = {}
        if B2C_TO_B2B_KEY:
            self.headers["X-Service-Key"] = B2C_TO_B2B_KEY

    async def unreserve(self, order_id: UUID, items: list[dict[str, str | int]]) -> None:
        payload = {
            "order_id": str(order_id),
            "items": items,
        }

        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=5.0) as client:
                response = await client.post(
                    "/api/v1/unreserve",
                    json=payload,
                    headers=self.headers,
                )
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            raise B2BUnavailableError("B2B inventory service unavailable") from exc

        if response.status_code >= 500:
            raise B2BUnavailableError("B2B inventory service unavailable")

        response.raise_for_status()
