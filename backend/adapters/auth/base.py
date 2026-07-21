from typing import Protocol


class IdentityAuthAdapter(Protocol):
    """Port for starting an authorization flow with an identity provider."""

    def build_authorization_url(
        self,
        redirect_to: str,
        code_challenge: str,
    ) -> str: ...
