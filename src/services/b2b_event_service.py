from src.repositories.b2b_event_repository import B2bEventRepository
from src.schemas.b2b_event import B2BEventCreateRequest, B2BEventCreateResponse
from src.repositories.cart_item_repository import CartItemRepository


class B2bEventService:
    def __init__(self, session):
        self.session = session
        self.repo = B2bEventRepository(session)
        self.cart_repo = CartItemRepository(session)

    async def create_event(
        self,
        payload: B2BEventCreateRequest,
    ):
        existing = await self.repo.get_by_idempotency_key(
            payload.idempotency_key
        )

        if existing:
            return B2BEventCreateResponse(
                accepted=True
            )

        reason_mapping = {
            "PRODUCT_BLOCKED": "PRODUCT_BLOCKED",
            "PRODUCT_DELETED": "PRODUCT_DELETED",
            "SKU_OUT_OF_STOCK": "OUT_OF_STOCK",
        }

        reason = reason_mapping[payload.event]

        await self.cart_repo.mark_unavailable(
            payload.sku_ids,
            reason,
        )

        event = await self.repo.create(payload)

        event.processed = True

        await self.session.commit()

        return B2BEventCreateResponse(
            accepted=True
        )