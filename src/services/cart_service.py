from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ConflictException, NotFoundException, ValidationException
from src.repositories.cart_repository import CartRepository
from src.schemas.cart import CartImageResponse, CartItemResponse, CartResponse
from src.services.b2b_catalog_client import B2BCatalogClient, B2BSkuData
from src.services.cart_identity import CartIdentity


class CartService:
    def __init__(self, session: AsyncSession):
        self.repo = CartRepository(session)
        self.session = session
        self.b2b_client = B2BCatalogClient()

    async def get_cart(self, identity: CartIdentity) -> CartResponse:
        cart = await self.repo.get_or_create_cart(identity)
        return await self._build_response(cart)

    async def add_item(self, identity: CartIdentity, sku_id: UUID, quantity: int) -> tuple[CartResponse, int]:
        if quantity < 1:
            raise ValidationException("Quantity must be greater than zero")

        sku = await self.b2b_client.get_sku(sku_id)
        if not sku or not self._is_sellable(sku):
            raise NotFoundException("SKU not found or product unavailable")
        if sku.available_quantity < quantity:
            raise ConflictException("Not enough stock")

        cart = await self.repo.get_or_create_cart(identity)
        item = await self.repo.get_item_by_sku(identity, sku_id)
        status_code = 201
        if item:
            new_quantity = item.quantity + quantity
            if sku.available_quantity < new_quantity:
                raise ConflictException("Not enough stock")
            await self.repo.update_quantity(item, new_quantity)
            status_code = 200
        else:
            await self.repo.add_item(cart, sku_id, sku.product_id, quantity, sku.unit_price)

        await self.session.commit()
        cart = await self.repo.get_or_create_cart(identity)
        return await self._build_response(cart), status_code

    async def update_item(self, identity: CartIdentity, sku_id: UUID, quantity: int) -> CartResponse:
        if quantity < 1:
            raise ValidationException("Quantity must be greater than zero")

        item = await self.repo.get_item_by_sku(identity, sku_id)
        if not item:
            raise NotFoundException("Cart item not found")

        sku = await self.b2b_client.get_sku(sku_id)
        if not sku or not self._is_sellable(sku):
            raise NotFoundException("SKU not found or product unavailable")
        if sku.available_quantity < quantity:
            raise ConflictException("Not enough stock")

        await self.repo.update_quantity(item, quantity)
        await self.session.commit()
        cart = await self.repo.get_or_create_cart(identity)
        return await self._build_response(cart)

    async def delete_item(self, identity: CartIdentity, sku_id: UUID) -> CartResponse:
        deleted = await self.repo.delete_item_by_sku(identity, sku_id)
        if not deleted:
            raise NotFoundException("Cart item not found")
        await self.session.commit()
        cart = await self.repo.get_or_create_cart(identity)
        return await self._build_response(cart)

    async def clear_cart(self, identity: CartIdentity) -> None:
        await self.repo.clear_cart(identity)
        await self.session.commit()

    async def merge_cart(self, identity: CartIdentity) -> CartResponse:
        if not identity.user_id or not identity.session_id:
            raise ValidationException("Authorization and X-Session-Id are required for cart merge")
        cart = await self.repo.merge_guest_cart(identity.session_id, identity.user_id)
        await self.session.commit()
        return await self._build_response(cart)

    async def _build_response(self, cart) -> CartResponse:
        items = list(cart.items or [])
        sku_data = await self.b2b_client.get_skus([item.sku_id for item in items])

        response_items: list[CartItemResponse] = []
        subtotal = 0
        unavailable_count = 0
        for item in items:
            sku = sku_data.get(item.sku_id)
            reason = self._unavailable_reason(sku, item.quantity)
            is_available = reason is None
            unit_price = sku.unit_price if sku else 0
            line_total = unit_price * item.quantity if is_available else 0
            if is_available:
                subtotal += line_total
            else:
                unavailable_count += 1

            response_items.append(
                CartItemResponse(
                    sku_id=item.sku_id,
                    product_id=sku.product_id if sku else item.product_id,
                    name=sku.name if sku else "",
                    sku_code=sku.sku_code if sku else None,
                    quantity=item.quantity,
                    unit_price=unit_price,
                    unit_price_at_add=item.unit_price_at_add,
                    line_total=line_total,
                    available_quantity=sku.available_quantity if sku else 0,
                    is_available=is_available,
                    unavailable_reason=reason,
                    image=self._image_response(sku.image if sku else None),
                )
            )

        return CartResponse(
            id=cart.id,
            items=response_items,
            items_count=sum(item.quantity for item in items),
            subtotal=subtotal,
            is_valid=unavailable_count == 0,
            updated_at=cart.updated_at or cart.created_at,
        )

    @staticmethod
    def _is_sellable(sku: B2BSkuData) -> bool:
        return (
            sku.found
            and not sku.product_deleted
            and not sku.product_blocked
            and sku.product_status == "MODERATED"
            and sku.available_quantity > 0
        )

    @staticmethod
    def _unavailable_reason(sku: B2BSkuData | None, requested_quantity: int) -> str | None:
        if not sku:
            return "PRODUCT_DELETED"
        if sku.product_deleted:
            return "PRODUCT_DELETED"
        if sku.product_blocked:
            return "PRODUCT_BLOCKED"
        if sku.product_status in {"ON_MODERATION", "CREATED"}:
            return "ON_MODERATION"
        if sku.product_status not in {None, "MODERATED"}:
            return "PRODUCT_DELISTED"
        if sku.available_quantity == 0:
            return "OUT_OF_STOCK"
        if sku.available_quantity < requested_quantity:
            return "OUT_OF_STOCK"
        return None

    @staticmethod
    def _image_response(image) -> CartImageResponse | None:
        if not image:
            return None
        if isinstance(image, str):
            return CartImageResponse(url=image, ordering=0, is_main=True)
        return CartImageResponse.model_validate(image)
