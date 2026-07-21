from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends

from backend.composition.auth import require_current_user
from backend.composition.moods import provide_mood_service
from backend.models.auth import AuthenticatedUser
from backend.schemas.moods import DailyMoodResponse, MoodPollRequest
from backend.services.mood_service import MoodService

router = APIRouter(prefix="/moods", tags=["moods"])


@router.post("", response_model=DailyMoodResponse)
async def record_mood(
    body: MoodPollRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[MoodService, Depends(provide_mood_service)],
) -> DailyMoodResponse:
    day_start, day_end = body.day_boundaries()
    mood = await service.record_mood(
        user.id,
        body.to_domain(),
        day_start,
        day_end,
    )
    return DailyMoodResponse.from_domain(mood)


@router.get("/{mood_date}", response_model=DailyMoodResponse)
async def get_mood(
    mood_date: date,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[MoodService, Depends(provide_mood_service)],
) -> DailyMoodResponse:
    mood = await service.get_mood(user.id, mood_date)
    return DailyMoodResponse.from_domain(mood)
