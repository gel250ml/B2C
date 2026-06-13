from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.favorite import Favorite
from src.repositories.favorite_repository import FavoriteRepository
from src.services.catalog_service import CatalogService
from src.schemas.catalog import PaginatedCatalogProductsResponse


class FavoriteService:
    def __init__(self, session: AsyncSession):
        self.repo = FavoriteRepository(session)
        self.session = session
        self.catalog_service = CatalogService(session)

    async def add_favorite(self, buyer_id: UUID, product_id: UUID) -> Favorite:
        existing = await self.repo.get_by_buyer_and_product(buyer_id, product_id)
        if existing:
            return existing

        favorite = Favorite(buyer_id=buyer_id, product_id=product_id)
        await self.repo.add(favorite)
        await self.session.commit()
        return favorite

    async def remove_favorite(self, buyer_id: UUID, product_id: UUID) -> None:
        await self.repo.delete(buyer_id, product_id)
        await self.session.commit()

    async def get_favorites(
            self,
            buyer_id: UUID,
            limit: int,
            offset: int,
    ) -> PaginatedCatalogProductsResponse:
        favorites = await self.repo.get_buyer_favorites(buyer_id, limit, offset)
        total_count = await self.repo.get_favorites_count(buyer_id)

        if not favorites:
            return PaginatedCatalogProductsResponse(
                items=[],
                total_count=total_count,
                limit=limit,
                offset=offset,
            )

        items = []
        for favorite in favorites:
            try:
                product = await self.catalog_service.get_visible_product_payload(favorite.product_id)
                if product:
                    item = self.catalog_service.build_catalog_product_item(product)
                    items.append(item)
            except Exception:
                continue

        return PaginatedCatalogProductsResponse(
            items=items,
            total_count=total_count,
            limit=limit,
            offset=offset,
        )