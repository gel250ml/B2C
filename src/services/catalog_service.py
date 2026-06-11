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

        skus = []
        for sku in product.get("skus", []):
            active_quantity = sku.get("active_quantity", 0) or 0
            skus.append(
                ProductSkuResponse(
                    id=sku["id"],
                    name=sku.get("name") or sku.get("sku_name") or "",
                    price=sku["price"],
                    discount=sku.get("discount", 0) or 0,
                    image=sku.get("image"),
                    active_quantity=active_quantity,
                    in_stock=active_quantity > 0,
                    characteristics=sku.get("characteristics", []),
                )
            )

        return ProductCardResponse(
            id=product["id"],
            slug=product.get("slug"),
            title=product["title"],
            description=product.get("description"),
            images=product.get("images", []),
            status=product["status"],
            characteristics=product.get("characteristics", []),
            skus=skus,
        )
