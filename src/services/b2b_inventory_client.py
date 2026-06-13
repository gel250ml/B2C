from uuid import UUID

import httpx

from src.core.config import B2B_URL, B2C_TO_B2B_KEY


class B2BUnavailableError(Exception):
    """Raised when B2B inventory service is temporarily unavailable."""


class ReserveFailedError(Exception):
    def __init__(self, failed_items: list[dict]):
        self.failed_items = failed_items
        super().__init__("Reserve failed")


class B2BInventoryClient:
    def __init__(self) -> None:
        self.base_url = B2B_URL
        self.headers: dict[str, str] = {}
        if B2C_TO_B2B_KEY:
            self.headers["X-Service-Key"] = B2C_TO_B2B_KEY


    async def reserve(self, idempotency_key: UUID, items: list[dict[str, str | int]]) -> None:
        payload = {
            "idempotency_key": str(idempotency_key),
            "items": items,
        }

        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=5.0) as client:
                response = await client.post(
                    "/api/v1/reserve",
                    json=payload,
                    headers=self.headers,
                )
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            raise B2BUnavailableError("B2B inventory service unavailable") from exc

        if response.status_code >= 500:
            raise B2BUnavailableError("B2B inventory service unavailable")

        if response.status_code == 409:
            raise ReserveFailedError(self._failed_items(response))

        response.raise_for_status()
        data = response.json()
        if data.get("reserved") is False:
            raise ReserveFailedError(data.get("failed_items", []))

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

    @staticmethod
    def _failed_items(response: httpx.Response) -> list[dict]:
        try:
            data = response.json()
        except ValueError:
            return []
        return data.get("failed_items", []) if isinstance(data, dict) else []
