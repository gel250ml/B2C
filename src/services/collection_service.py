from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundException
from src.repositories.collection_repository import CollectionRepository
from src.schemas.collection import (
    CollectionProductsResponse,
    CollectionResponseItem,
    CollectionsMetadataResponse,
    CollectionsResponse,
)
from src.schemas.catalog import CatalogProductCardResponse
from src.services.b2b_catalog_client import B2BCatalogClient
from src.services.catalog_service import CatalogService


class CollectionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = CollectionRepository(session)
        self.b2b_client = B2BCatalogClient()
        self.catalog_service = CatalogService(session)

    async def list_active_collections(self, limit: int = 10, offset: int = 0) -> CollectionsResponse:
        normalized_limit = self._clamp(limit, 1, 100)
        normalized_offset = max(offset, 0)
        total_count = await self.repo.count_active()
        collections = await self.repo.list_active(limit=normalized_limit, offset=normalized_offset)

        return CollectionsResponse(
            collections=[
                CollectionResponseItem(
                    id=collection.id,
                    title=collection.title,
                    description=collection.description,
                    cover_image_url=collection.cover_image_url,
                    target_url=collection.target_url,
                    priority=collection.priority,
                )
                for collection in collections
            ],
            metadata=CollectionsMetadataResponse(
                total_count=total_count,
                limit=normalized_limit,
                offset=normalized_offset,
            ),
        )

    async def get_collection_products(
        self,
        collection_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> CollectionProductsResponse:
        normalized_limit = self._clamp(limit, 1, 100)
        normalized_offset = max(offset, 0)

        collection = await self.repo.get_by_id(collection_id)
        if collection is None:
            raise NotFoundException("Collection not found")

        total_products = await self.repo.count_products(collection_id)
        product_ids = await self.repo.list_product_ids(
            collection_id,
            limit=normalized_limit,
            offset=normalized_offset,
        )
        products = await self.b2b_client.get_products_by_ids(product_ids)
        products_by_id = self._available_products_by_id(products)

        items: list[CatalogProductCardResponse] = []
        unavailable_ids: list[UUID] = []
        for product_id in product_ids:
            product = products_by_id.get(str(product_id))
            if product is None:
                unavailable_ids.append(product_id)
                continue
            items.append(self.catalog_service.build_catalog_product_card(product))

        return CollectionProductsResponse(
            collection_id=collection.id,
            collection_title=collection.title,
            items=items,
            unavailable_ids=unavailable_ids,
            total_products=total_products,
            limit=normalized_limit,
            offset=normalized_offset,
        )

    @staticmethod
    def _available_products_by_id(products: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for product in products:
            if CatalogService.is_hidden_product(product):
                continue
            product_id = product.get("id")
            if product_id is not None:
                result[str(product_id)] = product
        return result

    @staticmethod
    def _clamp(value: int, minimum: int, maximum: int) -> int:
        return min(max(value, minimum), maximum)
