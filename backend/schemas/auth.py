from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl

PkceChallenge = Annotated[
    str,
    Field(min_length=43, max_length=43, pattern=r"^[A-Za-z0-9_-]+$"),
]
AuthCodeVerifier = Annotated[
    str,
    Field(
        min_length=43,
        max_length=128,
        pattern=r"^[A-Za-z0-9._~-]+$",
        description="Original PKCE verifier used to derive the authorization challenge.",
    ),
]


class GoogleAuthorizeRequest(BaseModel):
    redirect_to: HttpUrl
    code_challenge: PkceChallenge


class GoogleAuthorizeResponse(BaseModel):
    authorization_url: str


class SessionExchangeRequest(BaseModel):
    auth_code: Annotated[str, Field(min_length=1, max_length=4096)]
    auth_code_verifier: AuthCodeVerifier


class SessionExchangeResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_at: datetime
    user_id: UUID


class SessionResponse(BaseModel):
    user_id: UUID
    email: str
    display_name: str | None
    avatar_url: str | None
