from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.dependencies import get_db
from src.services.payment_method_service import PaymentMethodService

router = APIRouter(
    prefix="/buyers/me/payment-methods",
    tags=["PaymentMethods"],
)

@router.get(
    "",
)
async def get_payment_methods(
        db: AsyncSession = Depends(get_db)
) -> None:
    return None
    service = PaymentMethodService(db)
    return await service.get_payment_methods()