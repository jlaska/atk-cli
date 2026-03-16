class ATKError(Exception):
    """Base exception for atk-cli errors."""


class AuthenticationError(ATKError):
    """Raised when authentication fails or tokens are missing/expired."""


class APIError(ATKError):
    """Raised when an API request fails."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class ConfigError(ATKError):
    """Raised for configuration problems."""
