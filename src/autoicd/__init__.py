"""AutoICD API — Python SDK.

Official Python SDK for the AutoICD API: clinical text to ICD-10-CM diagnosis codes.
"""

from .client import AutoICD
from .errors import (
    AuthenticationError,
    AutoICDError,
    NotFoundError,
    RateLimit,
    RateLimitError,
)
from .types import (
    AnonymizeResponse,
    ChapterInfo,
    CodeDetail,
    CodeDetailFull,
    CodeMatch,
    CodeOptions,
    CodeSearchResponse,
    CodingEntity,
    CodingResponse,
    PIIEntity,
    SearchOptions,
)

__all__ = [
    "AutoICD",
    # Errors
    "AutoICDError",
    "AuthenticationError",
    "RateLimitError",
    "NotFoundError",
    # Types
    "CodeOptions",
    "CodeMatch",
    "CodingEntity",
    "CodingResponse",
    "SearchOptions",
    "CodeDetail",
    "CodeDetailFull",
    "ChapterInfo",
    "CodeSearchResponse",
    "PIIEntity",
    "AnonymizeResponse",
    "RateLimit",
]
