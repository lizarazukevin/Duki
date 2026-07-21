from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from backend.composition.auth import require_current_user
from backend.composition.tasks import provide_goal_service
from backend.models.auth import AuthenticatedUser
from backend.schemas.goals import (
    GoalCreateRequest,
    GoalListResponse,
    GoalResponse,
    GoalUpdateRequest,
)
from backend.services.goal_service import GoalService

router = APIRouter(prefix="/goals", tags=["goals"])


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
    body: GoalCreateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[GoalService, Depends(provide_goal_service)],
) -> GoalResponse:
    goal = await service.create_goal(user.id, body.to_domain())
    return GoalResponse.from_domain(goal)


@router.get("", response_model=GoalListResponse)
async def list_goals(
    include_archived: Annotated[bool, Query()] = False,
    *,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[GoalService, Depends(provide_goal_service)],
) -> GoalListResponse:
    goals = await service.list_goals(user.id, include_archived)
    return GoalListResponse(items=[GoalResponse.from_domain(goal) for goal in goals])


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[GoalService, Depends(provide_goal_service)],
) -> GoalResponse:
    goal = await service.get_goal(user.id, goal_id)
    return GoalResponse.from_domain(goal)


@router.put("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: UUID,
    body: GoalUpdateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[GoalService, Depends(provide_goal_service)],
) -> GoalResponse:
    goal = await service.update_goal(user.id, goal_id, body.to_domain())
    return GoalResponse.from_domain(goal)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[GoalService, Depends(provide_goal_service)],
) -> Response:
    await service.delete_goal(user.id, goal_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
