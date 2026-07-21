from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from backend.composition.auth import require_current_user
from backend.composition.tasks import (
    provide_task_completion_service,
    provide_task_goal_service,
    provide_task_service,
)
from backend.models.auth import AuthenticatedUser
from backend.schemas.task_events import TaskCompletionRequest, TaskCompletionResponse
from backend.schemas.tasks import (
    TaskCreateRequest,
    TaskResponse,
    TaskTreeNodeResponse,
    TaskTreeResponse,
    TaskUpdateRequest,
)
from backend.services.task_completion_service import TaskCompletionService
from backend.services.task_goal_service import TaskGoalService
from backend.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/{task_id}/complete", response_model=TaskCompletionResponse)
async def complete_task(
    task_id: UUID,
    body: TaskCompletionRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[
        TaskCompletionService,
        Depends(provide_task_completion_service),
    ],
) -> TaskCompletionResponse:
    result = await service.complete_task(user.id, task_id, body.to_domain())
    return TaskCompletionResponse.from_domain(result)


@router.get("", response_model=TaskTreeResponse)
async def list_task_tree(
    include_archived: Annotated[bool, Query()] = False,
    *,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TaskService, Depends(provide_task_service)],
) -> TaskTreeResponse:
    task_tree = await service.list_task_tree(user.id, include_archived)
    return TaskTreeResponse(items=[TaskTreeNodeResponse.from_domain(node) for node in task_tree])


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    body: TaskCreateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TaskService, Depends(provide_task_service)],
) -> TaskResponse:
    task = await service.create_task(user.id, body.to_domain())
    return TaskResponse.from_domain(task)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TaskService, Depends(provide_task_service)],
) -> TaskResponse:
    task = await service.get_task(user.id, task_id)
    return TaskResponse.from_domain(task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    body: TaskUpdateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TaskService, Depends(provide_task_service)],
) -> TaskResponse:
    task = await service.update_task(user.id, task_id, body.to_domain())
    return TaskResponse.from_domain(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TaskService, Depends(provide_task_service)],
) -> Response:
    await service.delete_task(user.id, task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{task_id}/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def attach_goal(
    task_id: UUID,
    goal_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TaskGoalService, Depends(provide_task_goal_service)],
) -> Response:
    await service.attach_goal(user.id, task_id, goal_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{task_id}/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def detach_goal(
    task_id: UUID,
    goal_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TaskGoalService, Depends(provide_task_goal_service)],
) -> Response:
    await service.detach_goal(user.id, task_id, goal_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
