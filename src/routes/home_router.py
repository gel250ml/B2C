from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.dependencies import get_db
from src.schemas.banner import (
    BannerEventsRequest,
    BannerEventsResponse,
    BannerResponse,
    OpenAPIBannerResponseItem,
)
from src.services.banner_service import BannerService

router = APIRouter(tags=["Home"])


@router.get("/home/banners", response_model=BannerResponse)
async def get_home_banners(db: AsyncSession = Depends(get_db)) -> BannerResponse:
    service = BannerService(db)
    return await service.list_active_banners()


@router.get("/catalog/banners", response_model=list[OpenAPIBannerResponseItem], response_model_exclude_none=True)
async def get_catalog_banners(db: AsyncSession = Depends(get_db)) -> list[OpenAPIBannerResponseItem]:
    service = BannerService(db)
    return await service.list_active_openapi_banners()


@router.post(
    "/banner-events",
    response_model=BannerEventsResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_banner_events(
    payload: BannerEventsRequest,
    db: AsyncSession = Depends(get_db),
) -> BannerEventsResponse:
    service = BannerService(db)
    return await service.record_banner_events(payload.events)
