from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.composition.auth import require_current_user
from backend.composition.calendar import provide_calendar_availability_service
from backend.models.auth import AuthenticatedUser
from backend.schemas.calendar import (
    CalendarFreeBlockListResponse,
    CalendarFreeBlockQuery,
    CalendarFreeBlockResponse,
)
from backend.services.calendar_availability_service import CalendarAvailabilityService

router = APIRouter(prefix="/calendar-free-blocks", tags=["calendar-free-blocks"])


@router.get("", response_model=CalendarFreeBlockListResponse)
async def list_calendar_free_blocks(
    query: Annotated[CalendarFreeBlockQuery, Query()],
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[
        CalendarAvailabilityService,
        Depends(provide_calendar_availability_service),
    ],
) -> CalendarFreeBlockListResponse:
    blocks = await service.list_free_blocks(
        user.id,
        query.to_window(),
        query.minimum_minutes,
    )
    return CalendarFreeBlockListResponse(
        items=[CalendarFreeBlockResponse.from_domain(block) for block in blocks]
    )
