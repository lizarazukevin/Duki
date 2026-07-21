class DukiError(Exception):
    """Base class for expected domain failures."""

    code = "domain_error"
