from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from backend.composition.auth import require_current_user
from backend.composition.tasks import provide_task_service
from backend.models.auth import AuthenticatedUser
from backend.schemas.tasks import TaskCreateRequest, TaskResponse, TaskUpdateRequest
from backend.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


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
