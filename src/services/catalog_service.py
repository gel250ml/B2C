from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import B2B_URL, B2C_TO_B2B_KEY
from src.core.exceptions import NotFoundException
from src.repositories.catalog_repository import CatalogRepository
from src.schemas.catalog import ProductCardResponse, ProductSkuResponse


class CatalogService:
    def __init__(self, session: AsyncSession):
        self.repo = CatalogRepository(session)
        self.session = session

    async def get_product_card(self, product_id: UUID) -> ProductCardResponse:
        headers = {}
        if B2C_TO_B2B_KEY:
            headers["X-Service-Key"] = B2C_TO_B2B_KEY

        async with httpx.AsyncClient(base_url=B2B_URL, timeout=5.0) as client:
            response = await client.get(f"/api/v1/products/{product_id}", headers=headers)

        if response.status_code == 404:
            raise NotFoundException("Product not found")

        response.raise_for_status()
        product = response.json()

        if product.get("status") != "MODERATED" or product.get("deleted") is True:
            raise NotFoundException("Product not found")

        skus = [self._build_public_sku(sku) for sku in product.get("skus", [])]
        prices = [sku.price for sku in skus]
        old_prices = [sku.old_price for sku in skus if sku.old_price]

        return ProductCardResponse(
            id=product["id"],
            name=product.get("name") or product.get("title") or "",
            slug=product.get("slug"),
            category=product.get("category"),
            min_price=min(prices) if prices else 0,
            old_price=min(old_prices) if old_prices else None,
            has_stock=any(sku.available_quantity > 0 for sku in skus),
            rating=product.get("rating", 0) or 0,
            reviews_count=product.get("reviews_count", 0) or 0,
            images=product.get("images", []),
            seller=product.get("seller"),
            description=product.get("description"),
            attributes=product.get("attributes") or self._characteristics_to_attributes(product.get("characteristics", [])),
            skus=skus,
        )

    def _build_public_sku(self, sku: dict[str, Any]) -> ProductSkuResponse:
        base_price = sku.get("price", 0) or 0
        discount = sku.get("discount", 0) or 0
        public_price = max(base_price - discount, 0) if discount > 0 else base_price
        old_price = sku.get("old_price")
        if old_price is None and discount > 0:
            old_price = base_price

        return ProductSkuResponse(
            id=sku["id"],
            name=sku.get("name") or sku.get("sku_name") or "",
            sku_code=sku.get("sku_code"),
            price=public_price,
            old_price=old_price,
            available_quantity=sku.get("available_quantity", sku.get("active_quantity", 0)) or 0,
            attributes=sku.get("attributes") or self._characteristics_to_attributes(sku.get("characteristics", [])),
            images=self._build_sku_images(sku),
        )

    @staticmethod
    def _characteristics_to_attributes(characteristics: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            item["name"]: item.get("value")
            for item in characteristics
            if isinstance(item, dict) and item.get("name")
        }

    @staticmethod
    def _build_sku_images(sku: dict[str, Any]) -> list[dict[str, Any]]:
        images = sku.get("images")
        if images:
            return images

        image = sku.get("image")
        if not image:
            return []

        return [
            {
                "url": image,
                "ordering": 0,
                "is_main": True,
            }
        ]
