from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


# ── Coding ──────────────────────────────────────────────────────────


@dataclass
class CodeOptions:
    """Options for the ``code()`` method."""

    top_k: int | None = None
    """Number of ICD-10 candidates per entity (1-25, default 5)."""

    include_negated: bool | None = None
    """Include negated conditions in results (default True)."""


@dataclass
class CodeMatch:
    """A single ranked ICD-10 candidate."""

    code: str
    """ICD-10-CM code (e.g. ``"E11.21"``)."""

    description: str
    """Official code description."""

    similarity: float
    """0-1 cosine similarity score."""

    confidence: Literal["high", "moderate"]
    """Confidence level."""

    matched_term: str
    """The index term that produced this match."""


@dataclass
class CodingEntity:
    """An extracted diagnosis entity with ICD-10 candidates."""

    entity_text: str
    """Extracted text span."""

    entity_start: int
    """Character offset start."""

    entity_end: int
    """Character offset end."""

    negated: bool
    """Whether the condition was negated."""

    historical: bool
    """Whether this is historical/resolved."""

    family_history: bool
    """Whether this is a family member's condition."""

    uncertain: bool
    """Whether the entity is hedged/uncertain."""

    severity: str | None
    """Severity qualifier (e.g. ``"severe"``)."""

    codes: list[CodeMatch] = field(default_factory=list)
    """Ranked ICD-10 candidates."""

    merged_from: list[str] | None = None
    """Source texts if merged."""

    corrected_from: str | None = None
    """Original text before spell correction."""


@dataclass
class CodingResponse:
    """Complete coding result."""

    text: str
    """Input text that was processed."""

    provider: str
    """AI provider used for code matching."""

    entity_count: int
    """Total number of entities."""

    entities: list[CodingEntity] = field(default_factory=list)
    """Extracted entities sorted by position."""


# ── Code Search ─────────────────────────────────────────────────────


@dataclass
class SearchOptions:
    """Options for ``codes.search()``."""

    limit: int | None = None
    """1-100 results per page (default 20)."""

    offset: int | None = None
    """Pagination offset (default 0)."""


@dataclass
class CodeDetail:
    """Basic details for an ICD-10-CM code."""

    code: str
    short_description: str
    long_description: str
    is_billable: bool


@dataclass
class ChapterInfo:
    """ICD-10-CM chapter classification."""

    number: int
    """Chapter number (1-22)."""

    range: str
    """Code range (e.g. ``"E00-E89"``)."""

    title: str
    """Chapter title."""


@dataclass
class CodeDetailFull(CodeDetail):
    """Comprehensive details for an ICD-10-CM code including hierarchy and synonyms."""

    synonyms: dict[str, list[str]] = field(default_factory=dict)
    """Synonyms grouped by source: ``"snomed"``, ``"umls"``, ``"icd10_augmented"``."""

    cross_references: dict[str, list[str]] = field(default_factory=dict)
    """Cross-reference IDs grouped by source: ``"snomed"`` (SNOMED CT concept IDs), ``"umls"`` (UMLS CUIs)."""

    parent: CodeDetail | None = None
    """Parent code in the ICD-10 hierarchy, or ``None`` for top-level categories."""

    children: list[CodeDetail] = field(default_factory=list)
    """Direct child codes in the ICD-10 hierarchy."""

    chapter: ChapterInfo | None = None
    """ICD-10-CM chapter this code belongs to."""

    block: str | None = None
    """Code block range (e.g. ``"E08-E13"``)."""


@dataclass
class CodeSearchResponse:
    """Search results for ICD-10-CM codes."""

    query: str
    count: int
    codes: list[CodeDetail] = field(default_factory=list)


# ── Anonymization ───────────────────────────────────────────────────


@dataclass
class PIIEntity:
    """A detected PII entity."""

    text: str
    """Original PII text."""

    start: int
    """Character offset start."""

    end: int
    """Character offset end."""

    label: str
    """PII type: NAME, DATE, SSN, PHONE, EMAIL, ADDRESS, MRN, AGE."""

    replacement: str
    """Replacement placeholder (e.g. ``"[NAME]"``)."""


@dataclass
class AnonymizeResponse:
    """Result of PHI de-identification."""

    original_text: str
    anonymized_text: str
    pii_count: int
    pii_entities: list[PIIEntity] = field(default_factory=list)
