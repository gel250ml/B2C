from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.dependencies import get_db
from src.schemas.b2b_event import B2BEventCreateRequest, B2BEventCreateResponse
from src.services.b2b_event_service import B2bEventService

router = APIRouter(
    prefix="/b2b/events",
    tags=["B2B Events"],
)


@router.post("", response_model=B2BEventCreateResponse)
async def create_event(
    payload: B2BEventCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> B2BEventCreateResponse:
    service = B2bEventService(db)
    return await service.create_event(payload)
