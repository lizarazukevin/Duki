from typing import Annotated

from pydantic import BaseModel, Field, HttpUrl

PkceChallenge = Annotated[
    str,
    Field(min_length=43, max_length=43, pattern=r"^[A-Za-z0-9_-]+$"),
]


class GoogleAuthorizeRequest(BaseModel):
    redirect_to: HttpUrl
    code_challenge: PkceChallenge


class GoogleAuthorizeResponse(BaseModel):
    authorization_url: str
