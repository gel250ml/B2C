from uuid import UUID

from src.repositories.b2b_event_repository import B2bEventRepository
from src.repositories.cart_item_repository import CartItemRepository
from src.schemas.b2b_event import B2BEventCreateRequest, B2BEventCreateResponse


class B2bEventService:
    def __init__(self, session):
        self.session = session
        self.repo = B2bEventRepository(session)
        self.cart_repo = CartItemRepository(session)

    async def create_event(
        self,
        payload: B2BEventCreateRequest,
    ) -> B2BEventCreateResponse:
        existing = await self.repo.get_by_idempotency_key(
            payload.idempotency_key
        )

        if existing:
            return B2BEventCreateResponse(accepted=True)

        reason_mapping = {
            "PRODUCT_BLOCKED": "PRODUCT_BLOCKED",
            "PRODUCT_DELETED": "PRODUCT_DELETED",
            "SKU_OUT_OF_STOCK": "OUT_OF_STOCK",
        }

        reason = reason_mapping.get(payload.event_type)
        if reason is not None:
            sku_ids = self._extract_sku_ids(payload)
            if sku_ids:
                await self.cart_repo.mark_unavailable(sku_ids, reason)
            else:
                product_id = getattr(payload.payload, "product_id", None)
                if product_id is not None:
                    await self.cart_repo.mark_unavailable_by_product_id(product_id, reason)

        event = await self.repo.create(payload)
        event.processed = True

        await self.session.commit()

        return B2BEventCreateResponse(accepted=True)

    @staticmethod
    def _extract_sku_ids(payload: B2BEventCreateRequest) -> list[UUID]:
        sku_ids = getattr(payload.payload, "sku_ids", None)
        if sku_ids:
            return list(sku_ids)

        sku_id = getattr(payload.payload, "sku_id", None)
        if sku_id:
            return [sku_id]

        return []
