class DukiError(Exception):
    """Base class for expected domain failures."""

    code = "domain_error"
    status_code = 400


class AuthConfigurationError(DukiError):
    code = "auth_configuration_error"
    status_code = 503


class FeatureDisabledError(DukiError):
    code = "feature_disabled"
    status_code = 503


class RedirectNotAllowedError(DukiError):
    code = "redirect_not_allowed"
    status_code = 422
