from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from backend.composition.auth import require_current_user
from backend.composition.tasks import provide_task_service
from backend.models.auth import AuthenticatedUser
from backend.schemas.tasks import TaskCreateRequest, TaskResponse
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
