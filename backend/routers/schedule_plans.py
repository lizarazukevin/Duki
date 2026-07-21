from typing import Annotated

from fastapi import APIRouter, Depends

from backend.composition.auth import require_current_user
from backend.composition.scheduler import provide_scheduler_service
from backend.models.auth import AuthenticatedUser
from backend.schemas.scheduler import SchedulePlanRequest, SchedulePlanResponse
from backend.services.scheduler_service import SchedulerService

router = APIRouter(prefix="/schedule-plans", tags=["schedule-plans"])


@router.post("", response_model=SchedulePlanResponse)
async def build_schedule_plan(
    body: SchedulePlanRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[SchedulerService, Depends(provide_scheduler_service)],
) -> SchedulePlanResponse:
    plan = await service.build_plan(
        user.id,
        body.plan_date,
        body.to_window(),
        body.minimum_block_minutes,
    )
    return SchedulePlanResponse.from_domain(plan)
