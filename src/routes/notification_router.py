from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.dependencies import get_db
from src.services.notification_service import NotificationService

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)

@router.get(
    ""
)
async def get_notifications(
        db: AsyncSession = Depends(get_db)
) -> None:
    return None
    service = NotificationService(db)
    return await service.get_notifications()