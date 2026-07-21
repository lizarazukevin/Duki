from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from backend.adapters.calendar.base import CalendarAdapter
from backend.constants import PRIMARY_CALENDAR_ID
from backend.models.calendar import (
    CalendarEvent,
    CalendarSyncWindow,
    TaskCalendarEventLink,
)
from backend.repositories.auth import AuthRepository
from backend.repositories.calendar import CalendarRepository
from backend.repositories.tasks import TaskRepository


@dataclass(frozen=True, slots=True)
class TaskCalendarResult:
    linked: bool
    event: CalendarEvent | None


class TaskCalendarService:
    """Create or update the exact Google event linked to a user-owned task."""

    def __init__(
        self,
        calendar_adapter: CalendarAdapter,
        auth_repository: AuthRepository,
        calendar_repository: CalendarRepository,
        task_repository: TaskRepository,
    ) -> None:
        self._calendar_adapter = calendar_adapter
        self._auth_repository = auth_repository
        self._calendar_repository = calendar_repository
        self._task_repository = task_repository

    async def save_task_event(
        self,
        user_id: UUID,
        task_id: UUID,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> TaskCalendarResult:
        task = await self._task_repository.get_task(user_id, task_id)
        link = await self._calendar_repository.get_task_event_link(user_id, task_id)
        if start_time is None or end_time is None:
            if link is None:
                return TaskCalendarResult(linked=False, event=None)
            start_time = link.start_time
            end_time = link.end_time
            if task.estimated_minutes is not None:
                end_time = start_time + timedelta(minutes=task.estimated_minutes)

        CalendarSyncWindow(start_time=start_time, end_time=end_time)
        credentials = await self._auth_repository.get_google_credentials(user_id)
        if link is None:
            written = await self._calendar_adapter.create_event(
                credentials=credentials,
                title=task.title,
                description=task.description,
                start_time=start_time,
                end_time=end_time,
                calendar_id=PRIMARY_CALENDAR_ID,
            )
        else:
            written = await self._calendar_adapter.update_event(
                credentials=credentials,
                provider_event_id=link.provider_event_id,
                title=task.title,
                description=task.description,
                start_time=start_time,
                end_time=end_time,
                calendar_id=link.provider_calendar_id,
            )

        if written.refreshed_credentials is not None:
            await self._auth_repository.save_google_credentials(written.refreshed_credentials)
        event = written.event
        await self._calendar_repository.upsert_task_event_link(
            TaskCalendarEventLink(
                user_id=user_id,
                task_id=task_id,
                provider_event_id=event.provider_event_id,
                provider_calendar_id=event.provider_calendar_id,
                start_time=event.start_time,
                end_time=event.end_time,
            )
        )
        await self._calendar_repository.upsert_events((event,))
        return TaskCalendarResult(linked=True, event=event)
