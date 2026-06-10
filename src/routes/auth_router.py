from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.dependencies import get_db
from src.services.auth_service import AuthService

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)

@router.post(
    "/register",
)
async def register_user(
        db: AsyncSession = Depends(get_db),
) -> None:
    return None
    service = AuthService(db)
    return await service.register_user()