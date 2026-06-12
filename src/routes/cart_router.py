from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.dependencies import get_db
from src.schemas.cart import CartItemCreateRequest, CartItemQuantityRequest, CartResponse
from src.services.cart_identity import CartIdentity, get_cart_identity, get_merge_identity
from src.services.cart_service import CartService

router = APIRouter(
    prefix="/cart",
    tags=["Cart"],
)


@router.get("", response_model=CartResponse)
async def get_cart(
    identity: CartIdentity = Depends(get_cart_identity),
    db: AsyncSession = Depends(get_db),
) -> CartResponse:
    service = CartService(db)
    return await service.get_cart(identity)


@router.post("/items", response_model=CartResponse)
async def add_cart_item(
    payload: CartItemCreateRequest,
    response: Response,
    identity: CartIdentity = Depends(get_cart_identity),
    db: AsyncSession = Depends(get_db),
) -> CartResponse:
    service = CartService(db)
    cart, status_code = await service.add_item(identity, payload.sku_id, payload.quantity)
    response.status_code = status_code
    return cart


@router.patch("/items/{sku_id}", response_model=CartResponse)
async def update_cart_item(
    sku_id: UUID,
    payload: CartItemQuantityRequest,
    identity: CartIdentity = Depends(get_cart_identity),
    db: AsyncSession = Depends(get_db),
) -> CartResponse:
    service = CartService(db)
    return await service.update_item(identity, sku_id, payload.quantity)


@router.delete("/items/{sku_id}", response_model=CartResponse)
async def delete_cart_item(
    sku_id: UUID,
    identity: CartIdentity = Depends(get_cart_identity),
    db: AsyncSession = Depends(get_db),
) -> CartResponse:
    service = CartService(db)
    return await service.delete_item(identity, sku_id)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(
    identity: CartIdentity = Depends(get_cart_identity),
    db: AsyncSession = Depends(get_db),
) -> Response:
    service = CartService(db)
    await service.clear_cart(identity)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/merge", response_model=CartResponse)
async def merge_cart(
    identity: CartIdentity = Depends(get_merge_identity),
    db: AsyncSession = Depends(get_db),
) -> CartResponse:
    service = CartService(db)
    return await service.merge_cart(identity)
