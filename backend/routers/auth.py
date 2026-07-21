from typing import Annotated

from fastapi import APIRouter, Depends

from backend.composition.auth import provide_identity_auth_service
from backend.schemas.auth import GoogleAuthorizeRequest, GoogleAuthorizeResponse
from backend.services.identity_auth_service import IdentityAuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/google/authorize", response_model=GoogleAuthorizeResponse)
async def authorize_google(
    body: GoogleAuthorizeRequest,
    service: Annotated[
        IdentityAuthService,
        Depends(provide_identity_auth_service),
    ],
) -> GoogleAuthorizeResponse:
    authorization_url = service.authorization_url(
        redirect_to=str(body.redirect_to),
        code_challenge=body.code_challenge,
    )
    return GoogleAuthorizeResponse(authorization_url=authorization_url)
