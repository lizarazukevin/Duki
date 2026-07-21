from typing import Annotated

from fastapi import APIRouter, Depends

from backend.composition.auth import require_current_user
from backend.composition.calendar import provide_calendar_sync_service
from backend.models.auth import AuthenticatedUser
from backend.schemas.calendar import CalendarSyncRequest, CalendarSyncResponse
from backend.services.calendar_sync_service import CalendarSyncService

router = APIRouter(prefix="/calendar-events", tags=["calendar-events"])


@router.post("/sync", response_model=CalendarSyncResponse)
async def sync_calendar_events(
    body: CalendarSyncRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[CalendarSyncService, Depends(provide_calendar_sync_service)],
) -> CalendarSyncResponse:
    result = await service.sync(user_id=user.id, window=body.to_domain())
    return CalendarSyncResponse(
        events_upserted=result.events_upserted,
        events_cancelled=result.events_cancelled,
    )
