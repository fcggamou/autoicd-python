"""AutoICD API — Python SDK.

Official Python SDK for the AutoICD API: clinical text to ICD-10-CM and ICD-11 diagnosis codes.
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
    CrosswalkMapping,
    ICD11ChapterInfo,
    ICD11CodeDetail,
    ICD11CodeDetailFull,
    ICD11CodeSearchResponse,
    ICD11CodeSearchResult,
    ICFCodeDetail,
    ICFCodeResult,
    ICFCodeSummary,
    ICFCodingEntity,
    ICFCodingResponse,
    ICFCoreSetResult,
    ICFCrossReference,
    ICFSearchResponse,
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
    # ICD-11 Types
    "CrosswalkMapping",
    "ICD11CodeDetail",
    "ICD11ChapterInfo",
    "ICD11CodeDetailFull",
    "ICD11CodeSearchResult",
    "ICD11CodeSearchResponse",
    # ICF Types
    "ICFCodeSummary",
    "ICFCodeDetail",
    "ICFCodeResult",
    "ICFCodingEntity",
    "ICFCodingResponse",
    "ICFSearchResponse",
    "ICFCoreSetResult",
    "ICFCrossReference",
]
