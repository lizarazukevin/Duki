from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from starlette.requests import ClientDisconnect

from backend.composition.auth import require_current_user
from backend.composition.duck_sessions import (
    provide_duck_session_query_service,
    provide_duck_session_service,
)
from backend.constants import API_V1_PREFIX
from backend.errors import TranscriptionError
from backend.models.auth import AuthenticatedUser
from backend.schemas.duck_sessions import DuckSessionResponse
from backend.services.duck_session_query_service import DuckSessionQueryService
from backend.services.duck_session_service import DuckSessionService

router = APIRouter(prefix="/duck-sessions", tags=["duck-sessions"])
_AUDIO_REQUEST_BODY = {
    "requestBody": {
        "required": True,
        "content": {
            media_type: {"schema": {"type": "string", "format": "binary"}}
            for media_type in ("audio/m4a", "audio/mp4", "audio/mpeg", "audio/wav", "audio/webm")
        },
    }
}


@router.post(
    "",
    response_model=DuckSessionResponse,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=_AUDIO_REQUEST_BODY,
)
async def create_duck_session(
    request: Request,
    response: Response,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[DuckSessionService, Depends(provide_duck_session_service)],
) -> DuckSessionResponse:
    session = await service.process_audio(
        user_id=user.id,
        audio_chunks=_stream_audio(request),
        media_type=request.headers.get("content-type", ""),
    )
    response.headers["Location"] = f"{API_V1_PREFIX}/duck-sessions/{session.id}"
    return DuckSessionResponse.from_domain(session)


@router.get("/{session_id}", response_model=DuckSessionResponse)
async def get_duck_session(
    session_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[
        DuckSessionQueryService,
        Depends(provide_duck_session_query_service),
    ],
) -> DuckSessionResponse:
    session = await service.get_session(user.id, session_id)
    return DuckSessionResponse.from_domain(session)


async def _stream_audio(request: Request) -> AsyncIterator[bytes]:
    try:
        async for chunk in request.stream():
            yield chunk
    except ClientDisconnect as error:
        raise TranscriptionError("Audio upload was interrupted") from error
