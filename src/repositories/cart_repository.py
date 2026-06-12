from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Cart, CartItem
from src.services.cart_identity import CartIdentity


class CartRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _identity_filter(self, query, identity: CartIdentity):
        if identity.user_id:
            return query.where(Cart.buyer_id == identity.user_id)
        return query.where(Cart.session_id == identity.session_id)

    async def get_cart(self, identity: CartIdentity, with_items: bool = True) -> Cart | None:
        query = select(Cart)
        if with_items:
            query = query.options(selectinload(Cart.items))
        query = self._identity_filter(query, identity)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_or_create_cart(self, identity: CartIdentity) -> Cart:
        cart = await self.get_cart(identity)
        if cart:
            return cart

        cart = Cart(
            buyer_id=identity.user_id,
            session_id=None if identity.user_id else identity.session_id,
        )
        self.session.add(cart)
        await self.session.flush()
        await self.session.refresh(cart, attribute_names=["items"])
        return cart

    async def get_item_by_sku(self, identity: CartIdentity, sku_id: UUID) -> CartItem | None:
        query = (
            select(CartItem)
            .join(Cart)
            .where(CartItem.sku_id == sku_id)
        )
        query = self._identity_filter(query, identity)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def add_item(self, cart: Cart, sku_id: UUID, product_id: UUID | None, quantity: int, unit_price_at_add: int) -> CartItem:
        item = CartItem(
            cart_id=cart.id,
            sku_id=sku_id,
            product_id=product_id,
            quantity=quantity,
            unit_price_at_add=unit_price_at_add,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def update_quantity(self, item: CartItem, quantity: int) -> CartItem:
        item.quantity = quantity
        await self.session.flush()
        return item

    async def delete_item_by_sku(self, identity: CartIdentity, sku_id: UUID) -> bool:
        item = await self.get_item_by_sku(identity, sku_id)
        if not item:
            return False
        await self.session.delete(item)
        await self.session.flush()
        return True

    async def clear_cart(self, identity: CartIdentity) -> None:
        cart = await self.get_cart(identity, with_items=False)
        if not cart:
            return
        await self.session.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
        await self.session.flush()

    async def merge_guest_cart(self, session_id: UUID, user_id: UUID) -> Cart:
        guest_identity = CartIdentity(session_id=session_id)
        user_identity = CartIdentity(user_id=user_id)
        guest_cart = await self.get_cart(guest_identity)
        user_cart = await self.get_or_create_cart(user_identity)

        if not guest_cart:
            return user_cart

        user_by_sku = {item.sku_id: item for item in user_cart.items}
        for guest_item in list(guest_cart.items):
            user_item = user_by_sku.get(guest_item.sku_id)
            if user_item:
                user_item.quantity = max(user_item.quantity, guest_item.quantity)
                await self.session.delete(guest_item)
            else:
                guest_item.cart_id = user_cart.id
                user_by_sku[guest_item.sku_id] = guest_item

        await self.session.delete(guest_cart)
        await self.session.flush()
        await self.session.refresh(user_cart, attribute_names=["items"])
        return user_cart
