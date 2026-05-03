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

    output_system: str | None = None
    """Output coding system: ``"icd10"`` (default) or ``"icd11"``."""

    include_icf: bool | None = None
    """Include ICF functioning code results in the response."""

    include_icd11: bool | None = None
    """Include ICD-11 crosswalk codes per ICD-10 match."""

    include_snomed: bool | None = None
    """Include SNOMED CT concept IDs per ICD-10 match."""

    include_umls: bool | None = None
    """Include UMLS CUIs per ICD-10 match."""


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

    icd11_codes: list[str] = field(default_factory=list)
    """Mapped ICD-11 codes."""

    snomed_ids: list[str] = field(default_factory=list)
    """SNOMED CT concept IDs."""

    umls_cuis: list[str] = field(default_factory=list)
    """UMLS CUIs."""

    icf_categories: list[str] = field(default_factory=list)
    """Related ICF category codes."""


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

    icf_entities: list[ICFCodingEntity] | None = None
    """ICF functioning code results. Only present when include_icf=True."""


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
class CrosswalkMapping:
    """A crosswalk mapping between ICD-10 and ICD-11."""

    code: str
    """Mapped code (ICD-10 or ICD-11)."""

    description: str
    """Code description."""

    mapping_type: str
    """Mapping relationship: ``"equivalent"``, ``"narrower"``,
    ``"broader"``, or ``"approximate"``."""

    system: str
    """Target coding system: ``"icd10"`` or ``"icd11"``."""


@dataclass(frozen=True)
class ICFCrossReference:
    """A related ICF category from WHO Core Sets."""

    code: str
    """ICF code (e.g., "b5401")."""

    title: str
    """ICF code title."""

    component: str
    """Component letter: "b", "s", "d", or "e"."""


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

    icd11_mappings: list[CrosswalkMapping] = field(default_factory=list)
    """ICD-11 crosswalk mappings for this ICD-10 code."""

    icf_categories: list[ICFCrossReference] = field(default_factory=list)
    """Related ICF categories from WHO Core Sets."""


@dataclass
class CodeSearchResponse:
    """Search results for ICD-10-CM codes."""

    query: str
    count: int
    codes: list[CodeDetail] = field(default_factory=list)


# ── ICD-11 ──────────────────────────────────────────────────────────


@dataclass
class ICD11CodeDetail:
    """Basic details for an ICD-11 code."""

    code: str
    """ICD-11 code (e.g. ``"5A11"``)."""

    short_description: str
    """Abbreviated description."""

    long_description: str
    """Full official description."""

    foundation_uri: str | None
    """ICD-11 Foundation URI, or ``None`` if unavailable."""


@dataclass
class ICD11ChapterInfo:
    """ICD-11 chapter classification."""

    number: int
    """Chapter number."""

    title: str
    """Chapter title."""


@dataclass
class ICD11CodeDetailFull(ICD11CodeDetail):
    """Comprehensive ICD-11 code details with hierarchy, synonyms, and ICD-10 mappings."""

    synonyms: dict[str, list[str]] = field(default_factory=dict)
    """Synonyms grouped by source."""

    cross_references: dict[str, list[str]] = field(default_factory=dict)
    """Cross-reference IDs grouped by source."""

    parent: ICD11CodeDetail | None = None
    """Parent code in the ICD-11 hierarchy, or ``None`` for top-level categories."""

    children: list[ICD11CodeDetail] = field(default_factory=list)
    """Direct child codes in the ICD-11 hierarchy."""

    chapter: ICD11ChapterInfo | None = None
    """ICD-11 chapter this code belongs to."""

    block: str | None = None
    """Block within the chapter."""

    icd10_mappings: list[CrosswalkMapping] = field(default_factory=list)
    """ICD-10 crosswalk mappings for this ICD-11 code."""

    icf_categories: list[ICFCrossReference] = field(default_factory=list)
    """Related ICF categories (via ICD-10 bridge)."""


@dataclass
class ICD11CodeSearchResult:
    """A single ICD-11 code search result."""

    code: str
    """ICD-11 code."""

    short_description: str
    """Abbreviated description."""

    long_description: str
    """Full official description."""

    foundation_uri: str | None
    """ICD-11 Foundation URI, or ``None`` if unavailable."""


@dataclass
class ICD11CodeSearchResponse:
    """Search results for ICD-11 codes."""

    query: str
    count: int
    codes: list[ICD11CodeSearchResult] = field(default_factory=list)


# ── ICF ────────────────────────────────────────────────────────────


@dataclass
class ICFCodeSummary:
    """Lightweight ICF code reference."""

    code: str
    """ICF code (e.g. ``"b280"``)."""

    title: str
    """Code title."""

    component: str
    """ICF component: ``"b"``, ``"s"``, ``"d"``, or ``"e"``."""

    child_count: int = 0
    """Number of direct child codes."""


@dataclass
class ICFCodeDetail:
    """Full ICF code details."""

    code: str
    """ICF code."""

    title: str
    """Code title."""

    definition: str | None
    """Full definition text, or ``None`` if not available."""

    component: str
    """ICF component."""

    chapter: str
    """Chapter this code belongs to."""

    parent: ICFCodeSummary | None = None
    """Parent code in the ICF hierarchy, or ``None`` for top-level."""

    children: list[ICFCodeSummary] = field(default_factory=list)
    """Direct child codes."""

    inclusions: list[str] = field(default_factory=list)
    """Inclusion notes."""

    exclusions: list[str] = field(default_factory=list)
    """Exclusion notes."""

    index_terms: list[str] = field(default_factory=list)
    """Index terms for this code."""

    icd10_mappings: list[CrosswalkMapping] = field(default_factory=list)
    """Related ICD-10 codes from WHO Core Sets."""

    icd11_mappings: list[CrosswalkMapping] = field(default_factory=list)
    """Related ICD-11 codes (via ICD-10 bridge)."""

    cross_references: dict[str, list[str]] = field(default_factory=dict)
    """Cross-reference IDs: "snomed" (concept IDs), "umls" (CUIs)."""


@dataclass
class ICFCodeResult:
    """A single ICF code match."""

    code: str
    """Matched ICF code."""

    description: str
    """Code description."""

    component: str
    """ICF component."""

    similarity: float
    """0-1 cosine similarity score."""

    confidence: str
    """``"high"`` or ``"moderate"``."""

    matched_term: str
    """The index term that produced this match."""

    icd10_codes: list[str] = field(default_factory=list)
    """Related ICD-10 codes."""

    icd11_codes: list[str] = field(default_factory=list)
    """Related ICD-11 codes."""

    snomed_ids: list[str] = field(default_factory=list)
    """SNOMED CT concept IDs."""

    umls_cuis: list[str] = field(default_factory=list)
    """UMLS CUIs."""


@dataclass
class ICFCodingEntity:
    """ICF coding results for one entity."""

    entity_text: str
    """Extracted text span."""

    codes: list[ICFCodeResult] = field(default_factory=list)
    """Ranked ICF code candidates."""


@dataclass
class ICFSearchResponse:
    """ICF code search results."""

    query: str
    """The search query that was used."""

    count: int
    """Number of results returned."""

    codes: list[ICFCodeSummary] = field(default_factory=list)
    """Matching ICF codes."""


@dataclass
class ICFCoreSetResult:
    """ICF Core Set for an ICD-10 diagnosis."""

    icd10_code: str
    """ICD-10 code used to look up the core set."""

    condition_name: str
    """Condition name for this ICD-10 code."""

    brief: list[ICFCodeSummary] = field(default_factory=list)
    """Brief ICF Core Set codes."""

    comprehensive: list[ICFCodeSummary] = field(default_factory=list)
    """Comprehensive ICF Core Set codes."""


# ── LOINC ──────────────────────────────────────────────────────────


@dataclass
class LOINCCodeSummary:
    """Lightweight LOINC code reference."""

    code: str
    """LOINC code (e.g. ``"2345-7"``)."""

    long_common_name: str
    """Primary description."""

    short_name: str = ""
    """Abbreviated name."""

    class_name: str = ""
    """LOINC class (e.g. ``"CHEM"``)."""

    class_type: int = 1
    """1=Lab, 2=Clinical, 3=Claims, 4=Surveys."""

    order_obs: str = ""
    """Order, Observation, or Both."""


@dataclass
class LOINCCodeDetail:
    """Full LOINC code details."""

    code: str
    """LOINC code."""

    long_common_name: str
    """Primary description."""

    short_name: str = ""
    display_name: str = ""
    consumer_name: str = ""
    component: str = ""
    """What is measured (e.g. ``"Glucose"``)."""

    property: str = ""
    """Measurement property."""

    time_aspect: str = ""
    """Timing aspect."""

    system: str = ""
    """Specimen type."""

    scale_type: str = ""
    """Scale type."""

    method_type: str = ""
    """Method used."""

    class_name: str = ""
    class_type: int = 1
    definition: str | None = None
    order_obs: str = ""
    related_names: list[str] = field(default_factory=list)
    common_test_rank: int = 0
    common_order_rank: int = 0
    cross_references: dict[str, list[str]] = field(default_factory=dict)
    """Cross-reference IDs: ``"snomed"`` (concept IDs), ``"umls"`` (CUIs)."""


@dataclass
class LOINCSearchResponse:
    """LOINC code search results."""

    query: str
    count: int
    codes: list[LOINCCodeSummary] = field(default_factory=list)


@dataclass
class LOINCCodeResult:
    """A single LOINC code match."""

    code: str
    long_common_name: str
    component: str = ""
    system: str = ""
    similarity: float = 0.0
    confidence: str = "moderate"
    matched_term: str = ""
    snomed_ids: list[str] = field(default_factory=list)
    umls_cuis: list[str] = field(default_factory=list)


@dataclass
class LOINCCodingEntity:
    """LOINC coding results for one entity."""

    entity_text: str
    codes: list[LOINCCodeResult] = field(default_factory=list)


@dataclass
class LOINCCodingResponse:
    """Full LOINC coding response."""

    text: str
    provider: str = "sapbert"
    entity_count: int = 0
    results: list[LOINCCodingEntity] = field(default_factory=list)


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


# ── Chart Audit ─────────────────────────────────────────────────────

AuditCapability = Literal[
    "hcc", "radv", "specificity", "denial", "problem_list"
]

HCCModelChoice = Literal["v22", "v28", "both"]
HCCModelValue = Literal["v22", "v28"]


@dataclass
class AuditDocument:
    """One document in a longitudinal bundle."""

    id: str
    text: str
    type: str | None = None
    date: str | None = None


@dataclass
class AuditCode:
    """A code submitted for auditing."""

    code: str
    kind: Literal["icd10", "icd11", "cpt", "hcpcs"] = "icd10"


@dataclass
class AuditPatientContext:
    age: int | None = None
    sex: Literal["male", "female"] | None = None
    coverage: str | None = None


@dataclass
class AuditClaimContext:
    date_of_service: str | None = None
    place_of_service: str | None = None
    provider_type: str | None = None


@dataclass
class AuditPayerContext:
    id: str | None = None
    type: str | None = None


@dataclass
class AuditRatesOverride:
    cms_base_rate: float | None = None
    hospital_base_rate: float | None = None
    denial_rework_cost: float | None = None


@dataclass
class AuditContext:
    """Optional context that progressively unlocks richer findings."""

    patient: AuditPatientContext | None = None
    claim: AuditClaimContext | None = None
    payer: AuditPayerContext | None = None
    rates: AuditRatesOverride | None = None
    hcc_model: HCCModelChoice | None = None


@dataclass
class AuditRequest:
    """Chart audit input. Provide ``text`` OR ``documents``.

    ``codes`` is required unless ``capabilities`` is ``["problem_list"]`` only.
    """

    text: str | None = None
    documents: list[AuditDocument] | None = None
    codes: list[AuditCode] | None = None
    capabilities: list[AuditCapability] | None = None
    context: AuditContext | None = None


@dataclass
class EvidenceSpan:
    """A verbatim extract from the source text backing a finding."""

    document_id: str
    start: int
    end: int
    quote: str


@dataclass
class ConfirmedCode:
    code: str
    kind: str
    description: str
    evidence: list[EvidenceSpan] = field(default_factory=list)
    confidence: float = 0.0
    hcc_category: str | None = None
    raf_weight: float | None = None


@dataclass
class MissedCode:
    code: str
    kind: str
    description: str
    evidence: list[EvidenceSpan] = field(default_factory=list)
    confidence: float = 0.0
    hcc_category: str | None = None
    raf_weight: float | None = None
    estimated_revenue: float | None = None
    hcc_model: HCCModelValue | None = None


@dataclass
class UnsupportedCode:
    code: str
    kind: str
    description: str
    reason: str
    what_would_support_it: str
    radv_risk: Literal["high", "moderate", "low"]
    estimated_exposure: float | None = None


@dataclass
class MCCCCChange:
    from_: Literal["none", "cc", "mcc"]
    to: Literal["none", "cc", "mcc"]


@dataclass
class SpecificityUpgrade:
    from_code: str
    to_code: str
    from_description: str
    to_description: str
    evidence: list[EvidenceSpan] = field(default_factory=list)
    mcc_cc_change: MCCCCChange | None = None
    drg_impact: float | None = None


@dataclass
class DenialRisk:
    code: str
    kind: str
    description: str
    risk: Literal["high", "moderate", "low"]
    probability: float
    reasons: list[str] = field(default_factory=list)


@dataclass
class ProblemListDocumentRef:
    document_id: str
    date: str | None = None


@dataclass
class ProblemListEntry:
    condition: str
    icd10_code: str
    status: Literal["active", "resolved", "historical"]
    first_seen: ProblemListDocumentRef
    last_seen: ProblemListDocumentRef
    evidence: list[EvidenceSpan] = field(default_factory=list)


@dataclass
class AuditTotals:
    missed_raf: float
    estimated_revenue_recovery: float
    radv_exposure: float
    drg_upside: float
    codes_confirmed: int
    codes_missed: int
    codes_unsupported: int
    upgrades_available: int


@dataclass
class RatesUsed:
    cms_base_rate: float
    hospital_base_rate: float
    source: Literal["cms_national_2026", "customer_provided"]
    hcc_model: HCCModelChoice


@dataclass
class UpgradeHint:
    """Present when the server dropped capabilities that the caller's plan
    did not include."""

    denied_capabilities: list[AuditCapability]
    required_plan: str
    message: str


# ── Cross-standard Translate ────────────────────────────────────────

InteropSystem = Literal["icd10", "icd11", "snomed", "umls", "icf"]


@dataclass
class TranslateSource:
    code: str
    system: InteropSystem
    description: str | None = None


@dataclass
class TranslateMapping:
    """Single mapping row returned by ``/v1/translate``."""

    code: str
    description: str | None = None
    mapping_type: str | None = None
    component: str | None = None


@dataclass
class TranslateFrom:
    code: str
    system: InteropSystem


@dataclass
class TranslateRequest:
    """Chart translate input.

    ``from_`` is named with a trailing underscore to avoid shadowing the
    Python keyword. It serialises to the ``from`` JSON field on the wire.
    """

    from_: TranslateFrom
    to: list[InteropSystem] | None = None


@dataclass
class TranslateResponse:
    from_: TranslateSource
    mappings: dict[InteropSystem, list[TranslateMapping]]
    unsupported_targets: list[InteropSystem]
    provider: str


@dataclass
class AuditResponse:
    capabilities_run: list[AuditCapability]
    confirmed: list[ConfirmedCode]
    missed: list[MissedCode]
    unsupported: list[UnsupportedCode]
    specificity_upgrades: list[SpecificityUpgrade]
    denial_risk: list[DenialRisk]
    totals: AuditTotals
    provider: str
    rates_used: RatesUsed
    problem_list: list[ProblemListEntry] | None = None
    upgrade_hint: UpgradeHint | None = None
