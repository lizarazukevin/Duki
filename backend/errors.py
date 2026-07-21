class DukiError(Exception):
    """Base class for expected domain failures."""

    code = "domain_error"
    status_code = 400


class AuthConfigurationError(DukiError):
    code = "auth_configuration_error"
    status_code = 503


class CalendarPersistenceError(DukiError):
    code = "calendar_persistence_unavailable"
    status_code = 503


class CalendarAuthorizationError(DukiError):
    code = "calendar_authorization_failed"
    status_code = 401


class CalendarConfigurationError(DukiError):
    code = "calendar_configuration_error"
    status_code = 503


class CalendarRateLimitError(DukiError):
    code = "calendar_rate_limited"
    status_code = 503


class CalendarUnavailableError(DukiError):
    code = "calendar_unavailable"
    status_code = 503


class GoogleCredentialsNotFoundError(DukiError):
    code = "google_credentials_not_found"
    status_code = 409


class AuthenticationError(DukiError):
    code = "invalid_session"
    status_code = 401


class AuthorizationExchangeError(DukiError):
    code = "authorization_exchange_failed"
    status_code = 401


class CredentialEncryptionError(DukiError):
    code = "credential_encryption_failed"
    status_code = 500


class FeatureDisabledError(DukiError):
    code = "feature_disabled"
    status_code = 503


class IdentityProviderUnavailableError(DukiError):
    code = "identity_provider_unavailable"
    status_code = 503


class PersistenceError(DukiError):
    code = "persistence_unavailable"
    status_code = 503


class RedirectNotAllowedError(DukiError):
    code = "redirect_not_allowed"
    status_code = 422


class SessionRefreshError(DukiError):
    code = "session_refresh_failed"
    status_code = 401
