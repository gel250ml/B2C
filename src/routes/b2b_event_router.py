from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.dependencies import get_db
from src.services.b2b_event_service import B2bEventService

router = APIRouter(
    prefix="/b2b/events",
    tags=["B2B Events"],
)

@router.post(
    ""
)
async def create_event(
        db: AsyncSession = Depends(get_db),
) -> None:
    return None
    service = B2bEventService(db)
    return await service.create_event()
