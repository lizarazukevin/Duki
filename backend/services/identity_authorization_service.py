from urllib.parse import urlparse

from backend.adapters.auth.base import IdentityAuthorizationAdapter
from backend.errors import RedirectNotAllowedError


class IdentityAuthorizationService:
    """Start identity authorization without depending on a concrete provider."""

    def __init__(
        self,
        authorization_adapter: IdentityAuthorizationAdapter,
        allowed_redirect_hosts: frozenset[str],
    ) -> None:
        self._authorization_adapter = authorization_adapter
        self._allowed_redirect_hosts = allowed_redirect_hosts

    def authorization_url(self, redirect_to: str, code_challenge: str) -> str:
        hostname = urlparse(redirect_to).hostname
        if hostname is None or hostname.lower() not in self._allowed_redirect_hosts:
            raise RedirectNotAllowedError("OAuth redirect host is not allowed")
        return self._authorization_adapter.build_authorization_url(
            redirect_to=redirect_to,
            code_challenge=code_challenge,
        )
