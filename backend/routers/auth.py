from typing import Annotated

from fastapi import APIRouter, Depends

from backend.composition.auth import (
    provide_identity_authorization_service,
    require_current_user,
)
from backend.models.auth import AuthenticatedUser
from backend.schemas.auth import (
    GoogleAuthorizeRequest,
    GoogleAuthorizeResponse,
    SessionResponse,
)
from backend.services.identity_authorization_service import (
    IdentityAuthorizationService,
)

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
