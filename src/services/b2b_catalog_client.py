from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException

from src.core.config import B2B_URL, B2C_TO_B2B_KEY


@dataclass(frozen=True)
class B2BSkuData:
    sku_id: UUID
    product_id: UUID | None
    name: str
    sku_code: str | None
    unit_price: int
    available_quantity: int
    product_status: str | None
    product_deleted: bool
    product_blocked: bool
    image: dict[str, Any] | None
    product_title: str | None = None
    found: bool = True


class B2BCatalogClient:
    def __init__(self) -> None:
        self.base_url = B2B_URL
        self.headers = {}
        if B2C_TO_B2B_KEY:
            self.headers["X-Service-Key"] = B2C_TO_B2B_KEY

    async def get_skus(self, sku_ids: list[UUID]) -> dict[UUID, B2BSkuData]:
        if not sku_ids:
            return {}

        async with httpx.AsyncClient(base_url=self.base_url, timeout=5.0) as client:
            try:
                response = await client.get(
                    "/api/v1/products",
                    params={"sku_ids": ",".join(str(item) for item in sku_ids)},
                    headers=self.headers,
                )
            except httpx.HTTPError as exc:
                raise HTTPException(status_code=503, detail={"code": "SERVICE_UNAVAILABLE", "message": "B2B service unavailable"}) from exc

        if response.status_code >= 500:
            raise HTTPException(status_code=503, detail={"code": "SERVICE_UNAVAILABLE", "message": "B2B service unavailable"})
        response.raise_for_status()

        payload = response.json()
        products = payload.get("items", payload if isinstance(payload, list) else [])
        result: dict[UUID, B2BSkuData] = {}
        for product in products:
            if not isinstance(product, dict):
                continue
            product_id = self._to_uuid(product.get("id"))
            product_name = product.get("name") or product.get("title") or ""
            product_images = product.get("images") or []
            main_product_image = self._main_image(product_images)
            for sku in product.get("skus", []) or []:
                sku_id = self._to_uuid(sku.get("id"))
                if not sku_id:
                    continue
                result[sku_id] = B2BSkuData(
                    sku_id=sku_id,
                    product_id=product_id,
                    name=sku.get("name") or sku.get("sku_name") or product_name,
                    sku_code=sku.get("sku_code"),
                    unit_price=self._price(sku),
                    available_quantity=sku.get("available_quantity", sku.get("active_quantity", 0)) or 0,
                    product_status=product.get("status"),
                    product_deleted=bool(product.get("deleted", False)),
                    product_blocked=bool(product.get("blocked", False)) or product.get("status") in {"BLOCKED", "HARD_BLOCKED"},
                    image=self._main_image(sku.get("images") or []) or sku.get("image") or main_product_image,
                    product_title=product_name,
                )
        return result

    async def get_sku(self, sku_id: UUID) -> B2BSkuData | None:
        return (await self.get_skus([sku_id])).get(sku_id)

    @staticmethod
    def _to_uuid(value: Any) -> UUID | None:
        try:
            return UUID(str(value)) if value else None
        except ValueError:
            return None

    @staticmethod
    def _price(sku: dict[str, Any]) -> int:
        base_price = sku.get("price", 0) or 0
        discount = sku.get("discount", 0) or 0
        return max(base_price - discount, 0) if discount > 0 else base_price

    @staticmethod
    def _main_image(images: Any) -> dict[str, Any] | None:
        if not images:
            return None
        if isinstance(images, dict):
            return images
        if isinstance(images, list):
            for image in images:
                if isinstance(image, dict) and image.get("is_main"):
                    return image
            return images[0] if images and isinstance(images[0], dict) else None
        return {"url": str(images), "ordering": 0, "is_main": True}
