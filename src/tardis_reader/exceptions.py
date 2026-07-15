from __future__ import annotations


class TardisConfigError(Exception):
    """Raised when fetch options are missing, malformed, or mutually inconsistent."""


class TardisAuthError(Exception):
    """Raised when the Tardis.dev API rejects the supplied API key."""


class TardisAPIError(Exception):
    """Raised when the Tardis.dev API returns an unexpected error response."""

    def __init__(self, message: str, status_code: int | None = None, url: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.url = url
