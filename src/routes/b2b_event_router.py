from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.dependencies import get_db, verify_moderation_service_key
from src.schemas.b2b_event import B2BEventCreateRequest, B2BEventCreateResponse
from src.services.b2b_event_service import B2bEventService

router = APIRouter(
    prefix="/events/product",
    tags=["Events Product"],
)


@router.post("", response_model=B2BEventCreateResponse, status_code=202)
async def create_event(
    payload: B2BEventCreateRequest,
    db: AsyncSession = Depends(get_db),
    _service_key: None = Depends(verify_moderation_service_key),
) -> B2BEventCreateResponse:
    service = B2bEventService(db)
    return await service.create_event(payload)
