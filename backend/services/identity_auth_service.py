from urllib.parse import urlparse

from backend.adapters.auth.base import IdentityAuthAdapter
from backend.errors import RedirectNotAllowedError


class IdentityAuthService:
    """Start identity authorization without depending on a concrete provider."""

    def __init__(
        self,
        identity_adapter: IdentityAuthAdapter,
        allowed_redirect_hosts: frozenset[str],
    ) -> None:
        self._identity_adapter = identity_adapter
        self._allowed_redirect_hosts = allowed_redirect_hosts

    def authorization_url(self, redirect_to: str, code_challenge: str) -> str:
        hostname = urlparse(redirect_to).hostname
        if hostname is None or hostname.lower() not in self._allowed_redirect_hosts:
            raise RedirectNotAllowedError("OAuth redirect host is not allowed")
        return self._identity_adapter.build_authorization_url(
            redirect_to=redirect_to,
            code_challenge=code_challenge,
        )
