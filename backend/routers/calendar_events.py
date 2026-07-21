from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.composition.auth import require_current_user
from backend.composition.calendar import (
    provide_calendar_query_service,
    provide_calendar_sync_service,
)
from backend.models.auth import AuthenticatedUser
from backend.schemas.calendar import (
    CalendarEventListQuery,
    CalendarEventListResponse,
    CalendarEventResponse,
    CalendarSyncRequest,
    CalendarSyncResponse,
)
from backend.services.calendar_query_service import CalendarQueryService
from backend.services.calendar_sync_service import CalendarSyncService

router = APIRouter(prefix="/calendar-events", tags=["calendar-events"])


@router.get("", response_model=CalendarEventListResponse)
async def list_calendar_events(
    query: Annotated[CalendarEventListQuery, Query()],
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[CalendarQueryService, Depends(provide_calendar_query_service)],
) -> CalendarEventListResponse:
    result = await service.list_events(
        user_id=user.id,
        window=query.to_window(),
        limit=query.limit,
        encoded_cursor=query.cursor,
    )
    return CalendarEventListResponse(
        items=[CalendarEventResponse.from_domain(item) for item in result.items],
        next_cursor=result.next_cursor,
    )


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
