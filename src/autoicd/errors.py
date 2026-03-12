from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class RateLimit:
    """Rate limit info from API response headers."""

    limit: int
    remaining: int
    reset_at: datetime


class AutoICDError(Exception):
    """Base exception for AutoICD API errors."""

    def __init__(self, status: int, message: str) -> None:
        self.status = status
        super().__init__(message)


class AuthenticationError(AutoICDError):
    """Raised when the API key is invalid or revoked (401)."""

    def __init__(self, message: str = "Invalid API key") -> None:
        super().__init__(401, message)


class RateLimitError(AutoICDError):
    """Raised when the request limit is exceeded (429)."""

    def __init__(self, message: str, rate_limit: RateLimit) -> None:
        self.rate_limit = rate_limit
        super().__init__(429, message)


class NotFoundError(AutoICDError):
    """Raised when a resource is not found (404)."""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(404, message)
