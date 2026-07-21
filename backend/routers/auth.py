from typing import Annotated

from fastapi import APIRouter, Depends

from backend.composition.auth import (
    provide_identity_authorization_service,
    provide_session_exchange_service,
    require_current_user,
)
from backend.models.auth import AuthenticatedUser
from backend.schemas.auth import (
    GoogleAuthorizeRequest,
    GoogleAuthorizeResponse,
    SessionExchangeRequest,
    SessionExchangeResponse,
    SessionResponse,
)
from backend.services.identity_authorization_service import (
    IdentityAuthorizationService,
)
from backend.services.session_exchange_service import SessionExchangeService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/google/authorize", response_model=GoogleAuthorizeResponse)
async def authorize_google(
    body: GoogleAuthorizeRequest,
    service: Annotated[
        IdentityAuthorizationService,
        Depends(provide_identity_authorization_service),
    ],
) -> GoogleAuthorizeResponse:
    authorization_url = service.authorization_url(
        redirect_to=str(body.redirect_to),
        code_challenge=body.code_challenge,
    )
    return GoogleAuthorizeResponse(authorization_url=authorization_url)


@router.post("/sessions", response_model=SessionExchangeResponse)
async def exchange_session(
    body: SessionExchangeRequest,
    service: Annotated[
        SessionExchangeService,
        Depends(provide_session_exchange_service),
    ],
) -> SessionExchangeResponse:
    session = await service.exchange(
        auth_code=body.auth_code,
        auth_code_verifier=body.auth_code_verifier,
    )
    return SessionExchangeResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_at=session.expires_at,
        user_id=session.user.id,
    )


@router.get("/session", response_model=SessionResponse)
async def get_session(
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
) -> SessionResponse:
    return SessionResponse(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
    )
