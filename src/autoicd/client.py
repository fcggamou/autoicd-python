from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote, urlencode

import httpx

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
    LOINCCodeDetail,
    LOINCCodeResult,
    LOINCCodeSummary,
    LOINCCodingEntity,
    LOINCCodingResponse,
    LOINCSearchResponse,
    PIIEntity,
    SearchOptions,
    AuditCapability,
    AuditClaimContext,
    AuditCode,
    AuditContext,
    AuditDocument,
    AuditPatientContext,
    AuditPayerContext,
    AuditRatesOverride,
    AuditRequest,
    AuditResponse,
    AuditTotals,
    ConfirmedCode,
    DenialRisk,
    EvidenceSpan,
    MCCCCChange,
    MissedCode,
    ProblemListDocumentRef,
    ProblemListEntry,
    RatesUsed,
    SpecificityUpgrade,
    UnsupportedCode,
    UpgradeHint,
)

_DEFAULT_BASE_URL = "https://autoicdapi.com"
_DEFAULT_TIMEOUT = 30.0


class ICD10Codes:
    """Sub-resource for ICD-10-CM code lookups."""

    def __init__(self, client: AutoICD) -> None:
        self._client = client

    def search(
        self, query: str, options: SearchOptions | None = None
    ) -> CodeSearchResponse:
        """Search ICD-10-CM codes by description."""
        params: dict[str, str] = {"q": query}
        if options:
            if options.limit is not None:
                params["limit"] = str(options.limit)
            if options.offset is not None:
                params["offset"] = str(options.offset)
        data = self._client._get(f"/api/v1/icd10/codes/search?{urlencode(params)}")
        return CodeSearchResponse(
            query=data["query"],
            count=data["count"],
            codes=[CodeDetail(**c) for c in data["codes"]],
        )

    def get(self, code: str) -> CodeDetailFull:
        """Get full details for an ICD-10-CM code.

        Returns comprehensive info including synonyms (SNOMED CT, UMLS),
        hierarchy (parent/children), and chapter/block classification.
        """
        data = self._client._get(f"/api/v1/icd10/codes/{quote(code, safe='')}")
        return _parse_code_detail_full(data)



class ICD11Codes:
    """Sub-resource for ICD-11 code lookups."""

    def __init__(self, client: AutoICD) -> None:
        self._client = client

    def search(
        self, query: str, options: SearchOptions | None = None
    ) -> ICD11CodeSearchResponse:
        """Search ICD-11 codes by description."""
        params: dict[str, str] = {"q": query}
        if options:
            if options.limit is not None:
                params["limit"] = str(options.limit)
            if options.offset is not None:
                params["offset"] = str(options.offset)
        data = self._client._get(f"/api/v1/icd11/codes/search?{urlencode(params)}")
        return ICD11CodeSearchResponse(
            query=data["query"],
            count=data["count"],
            codes=[ICD11CodeSearchResult(**c) for c in data["codes"]],
        )

    def get(self, code: str) -> ICD11CodeDetailFull:
        """Get full details for an ICD-11 code.

        Returns comprehensive info including synonyms, hierarchy (parent/children),
        chapter/block classification, and ICD-10 crosswalk mappings.
        """
        data = self._client._get(f"/api/v1/icd11/codes/{quote(code, safe='')}")
        return _parse_icd11_code_detail_full(data)


class ICFCodes:
    """Sub-resource for ICF code lookups and coding."""

    def __init__(self, client: AutoICD) -> None:
        self._client = client

    def code(self, text: str, top_k: int = 5) -> ICFCodingResponse:
        """Code clinical text to ICF codes.

        Args:
            text: Clinical note or free-text input.
            top_k: Number of ICF candidates per entity (default 5).
        """
        data = self._client._post("/api/v1/icf/code", {"text": text, "top_k": top_k})
        return _parse_icf_coding_response(data)

    def lookup(self, code: str) -> ICFCodeDetail:
        """Get full details for an ICF code.

        Returns comprehensive info including definition, hierarchy
        (parent/children), inclusions, exclusions, and index terms.
        """
        data = self._client._get(f"/api/v1/icf/codes/{quote(code, safe='')}")
        return _parse_icf_code_detail(data)

    def search(
        self, query: str, limit: int = 20, offset: int = 0
    ) -> ICFSearchResponse:
        """Search ICF codes by description.

        Args:
            query: Search text.
            limit: Maximum results (default 20).
            offset: Pagination offset (default 0).
        """
        params: dict[str, str] = {"q": query, "limit": str(limit)}
        if offset:
            params["offset"] = str(offset)
        data = self._client._get(f"/api/v1/icf/codes/search?{urlencode(params)}")
        return _parse_icf_search_response(data)

    def core_set(self, icd10_code: str) -> ICFCoreSetResult:
        """Get the ICF Core Set for an ICD-10 diagnosis code.

        Args:
            icd10_code: An ICD-10-CM code (e.g. ``"M54.5"``).
        """
        data = self._client._get(f"/api/v1/icf/core-set/{quote(icd10_code, safe='')}")
        return _parse_icf_core_set_result(data)


class LOINCCodes:
    """Sub-resource for LOINC code lookups and coding."""

    def __init__(self, client: AutoICD) -> None:
        self._client = client

    def code(self, text: str, top_k: int = 5) -> LOINCCodingResponse:
        """Code clinical text to LOINC codes.

        Args:
            text: Clinical note or free-text input.
            top_k: Number of LOINC candidates per entity (default 5).
        """
        data = self._client._post("/api/v1/loinc/code", {"text": text, "top_k": top_k})
        return _parse_loinc_coding_response(data)

    def lookup(self, code: str) -> LOINCCodeDetail:
        """Get full details for a LOINC code.

        Returns comprehensive info including 6-axis classification,
        definition, related names, and cross-references.
        """
        data = self._client._get(f"/api/v1/loinc/codes/{quote(code, safe='')}")
        return _parse_loinc_code_detail(data)

    def search(
        self, query: str, limit: int = 20, offset: int = 0
    ) -> LOINCSearchResponse:
        """Search LOINC codes by description.

        Args:
            query: Search text.
            limit: Maximum results (default 20).
            offset: Pagination offset (default 0).
        """
        params: dict[str, str] = {"q": query, "limit": str(limit)}
        if offset:
            params["offset"] = str(offset)
        data = self._client._get(f"/api/v1/loinc/codes/search?{urlencode(params)}")
        return _parse_loinc_search_response(data)


class AutoICD:
    """Client for the AutoICD API.

    Args:
        api_key: Your API key (starts with ``sk_``).
        base_url: API base URL (default ``https://autoicdapi.com``).
        timeout: Request timeout in seconds (default 30).
        http_client: Optional ``httpx.Client`` instance for custom configuration.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key must be a non-empty string")

        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._owns_client = http_client is None
        self._http = http_client or httpx.Client(timeout=self._timeout)
        self.icd10 = ICD10Codes(self)
        self.icd11 = ICD11Codes(self)
        self.icf = ICFCodes(self)
        self.loinc = LOINCCodes(self)
        self.last_rate_limit: RateLimit | None = None

    def close(self) -> None:
        """Close the underlying HTTP client (only if we created it)."""
        if self._owns_client:
            self._http.close()

    def __enter__(self) -> AutoICD:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ── Public methods ──────────────────────────────────────────────

    def code(
        self, text: str, options: CodeOptions | None = None
    ) -> CodingResponse:
        """Code clinical text to ICD-10-CM diagnoses.

        Args:
            text: Clinical note or free-text input.
            options: Optional coding parameters.
        """
        body: dict[str, Any] = {"text": text}
        if options:
            if options.top_k is not None:
                body["top_k"] = options.top_k
            if options.include_negated is not None:
                body["include_negated"] = options.include_negated
            if options.output_system is not None:
                body["output_system"] = options.output_system
            if options.include_icf is not None:
                body["include_icf"] = options.include_icf
            if options.include_icd11 is not None:
                body["include_icd11"] = options.include_icd11
            if options.include_snomed is not None:
                body["include_snomed"] = options.include_snomed
            if options.include_umls is not None:
                body["include_umls"] = options.include_umls
        data = self._post("/api/v1/code", body)
        return _parse_coding_response(data)

    def anonymize(self, text: str) -> AnonymizeResponse:
        """De-identify PHI/PII in clinical text.

        Args:
            text: Clinical note containing PHI.
        """
        data = self._post("/api/v1/anonymize", {"text": text})
        return AnonymizeResponse(
            original_text=data["original_text"],
            anonymized_text=data["anonymized_text"],
            pii_count=data["pii_count"],
            pii_entities=[PIIEntity(**e) for e in data["pii_entities"]],
        )

    def audit(self, request: AuditRequest | dict[str, Any]) -> AuditResponse:
        """Audit a chart for HCC gaps, RADV risk, specificity, denial risk, and
        a reconciled problem list.

        Args:
            request: An :class:`AuditRequest` (or equivalent plain dict) with
                ``text`` or ``documents``, ``codes``, and optional
                ``capabilities`` and ``context``.
        """
        body = _audit_request_to_body(request)
        data = self._post("/api/v1/audit", body)
        return _parse_audit_response(data)

    # ── HTTP internals ──────────────────────────────────────────────

    def _get(self, path: str) -> Any:
        return self._request("GET", path)

    def _post(self, path: str, body: dict[str, Any]) -> Any:
        return self._request("POST", path, body=body)

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self._base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        response = self._http.request(
            method,
            url,
            headers=headers,
            json=body,
            timeout=self._timeout,
        )

        # Parse rate limit headers
        self._parse_rate_limit(response.headers)

        # Success
        if 200 <= response.status_code < 300:
            return response.json()

        # Error handling
        try:
            error_body = response.json()
            message = error_body.get("error", response.text)
        except Exception:
            message = response.text

        if response.status_code == 401:
            raise AuthenticationError(message)
        if response.status_code == 404:
            raise NotFoundError(message)
        if response.status_code == 429:
            rl = self.last_rate_limit or RateLimit(
                limit=0, remaining=0, reset_at=datetime.now(timezone.utc)
            )
            raise RateLimitError(message, rate_limit=rl)

        raise AutoICDError(response.status_code, message)

    def _parse_rate_limit(self, headers: httpx.Headers) -> None:
        limit = headers.get("X-RateLimit-Limit")
        remaining = headers.get("X-RateLimit-Remaining")
        reset_at = headers.get("X-RateLimit-Reset")

        if limit is not None and remaining is not None and reset_at is not None:
            self.last_rate_limit = RateLimit(
                limit=int(limit),
                remaining=int(remaining),
                reset_at=datetime.fromisoformat(reset_at),
            )
        else:
            self.last_rate_limit = None


# ── Response parsing helpers ────────────────────────────────────────


def _parse_code_match(data: dict[str, Any]) -> CodeMatch:
    return CodeMatch(
        code=data["code"],
        description=data["description"],
        similarity=data["similarity"],
        confidence=data["confidence"],
        matched_term=data["matched_term"],
        icd11_codes=data.get("icd11_codes", []),
        snomed_ids=data.get("snomed_ids", []),
        umls_cuis=data.get("umls_cuis", []),
        icf_categories=data.get("icf_categories", []),
    )


def _parse_entity(data: dict[str, Any]) -> CodingEntity:
    return CodingEntity(
        entity_text=data["entity_text"],
        entity_start=data["entity_start"],
        entity_end=data["entity_end"],
        negated=data["negated"],
        historical=data["historical"],
        family_history=data["family_history"],
        uncertain=data["uncertain"],
        severity=data.get("severity"),
        codes=[_parse_code_match(c) for c in data.get("codes", [])],
        merged_from=data.get("merged_from"),
        corrected_from=data.get("corrected_from"),
    )


def _parse_coding_response(data: dict[str, Any]) -> CodingResponse:
    icf_entities = None
    if data.get("icf_entities") is not None:
        icf_entities = [
            ICFCodingEntity(
                entity_text=e["entity_text"],
                codes=[_parse_icf_code_result(c) for c in e.get("codes", [])],
            )
            for e in data["icf_entities"]
        ]

    return CodingResponse(
        text=data["text"],
        provider=data["provider"],
        entity_count=data["entity_count"],
        entities=[_parse_entity(e) for e in data.get("entities", [])],
        icf_entities=icf_entities,
    )


def _parse_crosswalk_mappings(data: list[dict[str, Any]]) -> list[CrosswalkMapping]:
    return [CrosswalkMapping(**m) for m in data]


def _parse_icf_cross_reference(data: dict[str, Any]) -> ICFCrossReference:
    return ICFCrossReference(
        code=data["code"],
        title=data["title"],
        component=data["component"],
    )


def _parse_code_detail_full(data: dict[str, Any]) -> CodeDetailFull:
    parent_data = data.get("parent")
    parent = CodeDetail(**parent_data) if parent_data else None

    children = [CodeDetail(**c) for c in data.get("children", [])]

    chapter_data = data.get("chapter")
    chapter = ChapterInfo(**chapter_data) if chapter_data else None

    icd11_raw = data.get("icd11_mappings")
    icd11_mappings = _parse_crosswalk_mappings(icd11_raw) if icd11_raw else []

    return CodeDetailFull(
        code=data["code"],
        short_description=data["short_description"],
        long_description=data["long_description"],
        is_billable=data["is_billable"],
        synonyms=data.get("synonyms", {}),
        cross_references=data.get("cross_references", {}),
        parent=parent,
        children=children,
        chapter=chapter,
        block=data.get("block"),
        icd11_mappings=icd11_mappings,
        icf_categories=[
            _parse_icf_cross_reference(c)
            for c in data.get("icf_categories", [])
        ],
    )


def _parse_icd11_code_detail_full(data: dict[str, Any]) -> ICD11CodeDetailFull:
    parent_data = data.get("parent")
    parent = ICD11CodeDetail(**parent_data) if parent_data else None

    children = [ICD11CodeDetail(**c) for c in data.get("children", [])]

    chapter_data = data.get("chapter")
    chapter = ICD11ChapterInfo(**chapter_data) if chapter_data else None

    icd10_mappings = _parse_crosswalk_mappings(data.get("icd10_mappings", []))

    return ICD11CodeDetailFull(
        code=data["code"],
        short_description=data["short_description"],
        long_description=data["long_description"],
        foundation_uri=data.get("foundation_uri"),
        synonyms=data.get("synonyms", {}),
        cross_references=data.get("cross_references", {}),
        parent=parent,
        children=children,
        chapter=chapter,
        block=data.get("block"),
        icd10_mappings=icd10_mappings,
        icf_categories=[
            _parse_icf_cross_reference(c)
            for c in data.get("icf_categories", [])
        ],
    )


# ── ICF response parsing helpers ───────────────────────────────────


def _parse_icf_code_summary(data: dict[str, Any]) -> ICFCodeSummary:
    return ICFCodeSummary(
        code=data["code"],
        title=data["title"],
        component=data["component"],
        child_count=data.get("child_count", 0),
    )


def _parse_icf_code_detail(data: dict[str, Any]) -> ICFCodeDetail:
    parent_data = data.get("parent")
    parent = _parse_icf_code_summary(parent_data) if parent_data else None

    children = [_parse_icf_code_summary(c) for c in data.get("children", [])]

    return ICFCodeDetail(
        code=data["code"],
        title=data["title"],
        definition=data.get("definition"),
        component=data["component"],
        chapter=data["chapter"],
        parent=parent,
        children=children,
        inclusions=data.get("inclusions", []),
        exclusions=data.get("exclusions", []),
        index_terms=data.get("index_terms", []),
        icd10_mappings=_parse_crosswalk_mappings(data.get("icd10_mappings", [])),
        icd11_mappings=_parse_crosswalk_mappings(data.get("icd11_mappings", [])),
        cross_references=data.get("cross_references", {}),
    )


def _parse_icf_code_result(data: dict[str, Any]) -> ICFCodeResult:
    return ICFCodeResult(
        code=data["code"],
        description=data["description"],
        component=data["component"],
        similarity=data["similarity"],
        confidence=data["confidence"],
        matched_term=data["matched_term"],
        icd10_codes=data.get("icd10_codes", []),
        icd11_codes=data.get("icd11_codes", []),
        snomed_ids=data.get("snomed_ids", []),
        umls_cuis=data.get("umls_cuis", []),
    )


def _parse_icf_coding_entity(data: dict[str, Any]) -> ICFCodingEntity:
    return ICFCodingEntity(
        entity_text=data["entity_text"],
        codes=[_parse_icf_code_result(c) for c in data.get("codes", [])],
    )


def _parse_icf_coding_response(data: dict[str, Any]) -> ICFCodingResponse:
    return ICFCodingResponse(
        text=data["text"],
        provider=data["provider"],
        entity_count=data["entity_count"],
        results=[_parse_icf_coding_entity(e) for e in data.get("results", [])],
    )


def _parse_icf_search_response(data: dict[str, Any]) -> ICFSearchResponse:
    return ICFSearchResponse(
        query=data["query"],
        count=data["count"],
        codes=[_parse_icf_code_summary(c) for c in data.get("codes", [])],
    )


def _parse_icf_core_set_result(data: dict[str, Any]) -> ICFCoreSetResult:
    return ICFCoreSetResult(
        icd10_code=data["icd10_code"],
        condition_name=data["condition_name"],
        brief=[_parse_icf_code_summary(c) for c in data.get("brief", [])],
        comprehensive=[_parse_icf_code_summary(c) for c in data.get("comprehensive", [])],
    )


# ── LOINC response parsing helpers ──────────────────────────────────


def _parse_loinc_code_summary(data: dict[str, Any]) -> LOINCCodeSummary:
    return LOINCCodeSummary(
        code=data["code"],
        long_common_name=data["long_common_name"],
        short_name=data.get("short_name", ""),
        class_name=data.get("class_name", ""),
        class_type=data.get("class_type", 1),
        order_obs=data.get("order_obs", ""),
    )


def _parse_loinc_code_detail(data: dict[str, Any]) -> LOINCCodeDetail:
    return LOINCCodeDetail(
        code=data["code"],
        long_common_name=data["long_common_name"],
        short_name=data.get("short_name", ""),
        display_name=data.get("display_name", ""),
        consumer_name=data.get("consumer_name", ""),
        component=data.get("component", ""),
        property=data.get("property", ""),
        time_aspect=data.get("time_aspect", ""),
        system=data.get("system", ""),
        scale_type=data.get("scale_type", ""),
        method_type=data.get("method_type", ""),
        class_name=data.get("class_name", ""),
        class_type=data.get("class_type", 1),
        definition=data.get("definition"),
        order_obs=data.get("order_obs", ""),
        related_names=data.get("related_names", []),
        common_test_rank=data.get("common_test_rank", 0),
        common_order_rank=data.get("common_order_rank", 0),
        cross_references=data.get("cross_references", {}),
    )


def _parse_loinc_search_response(data: dict[str, Any]) -> LOINCSearchResponse:
    return LOINCSearchResponse(
        query=data["query"],
        count=data["count"],
        codes=[_parse_loinc_code_summary(c) for c in data.get("codes", [])],
    )


def _parse_loinc_code_result(data: dict[str, Any]) -> LOINCCodeResult:
    return LOINCCodeResult(
        code=data["code"],
        long_common_name=data["long_common_name"],
        component=data.get("component", ""),
        system=data.get("system", ""),
        similarity=data["similarity"],
        confidence=data["confidence"],
        matched_term=data["matched_term"],
        snomed_ids=data.get("snomed_ids", []),
        umls_cuis=data.get("umls_cuis", []),
    )


def _parse_loinc_coding_response(data: dict[str, Any]) -> LOINCCodingResponse:
    return LOINCCodingResponse(
        text=data["text"],
        provider=data["provider"],
        entity_count=data["entity_count"],
        results=[
            LOINCCodingEntity(
                entity_text=e["entity_text"],
                codes=[_parse_loinc_code_result(c) for c in e.get("codes", [])],
            )
            for e in data.get("results", [])
        ],
    )


# ── Audit helpers ───────────────────────────────────────────────────


def _dataclass_to_dict(value: Any) -> Any:
    """Convert dataclasses to plain dicts, skipping ``None`` fields. Also
    handles the ``mcc_cc_change.from_`` Python-keyword quirk."""
    from dataclasses import asdict, is_dataclass

    if is_dataclass(value):
        result: dict[str, Any] = {}
        for key, val in asdict(value).items():
            if val is None:
                continue
            out_key = "from" if key == "from_" else key
            result[out_key] = _clean(val)
        return result
    return _clean(value)


def _clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            ("from" if k == "from_" else k): _clean(v)
            for k, v in value.items()
            if v is not None
        }
    if isinstance(value, list):
        return [_clean(v) for v in value]
    return value


def _audit_request_to_body(request: AuditRequest | dict[str, Any]) -> dict[str, Any]:
    if isinstance(request, dict):
        return _clean(request)
    return _dataclass_to_dict(request)


def _parse_evidence_span(data: dict[str, Any]) -> EvidenceSpan:
    return EvidenceSpan(
        document_id=data["document_id"],
        start=data["start"],
        end=data["end"],
        quote=data["quote"],
    )


def _parse_confirmed(data: dict[str, Any]) -> ConfirmedCode:
    return ConfirmedCode(
        code=data["code"],
        kind=data["kind"],
        description=data["description"],
        evidence=[_parse_evidence_span(e) for e in data.get("evidence", [])],
        confidence=data["confidence"],
        hcc_category=data.get("hcc_category"),
        raf_weight=data.get("raf_weight"),
    )


def _parse_missed(data: dict[str, Any]) -> MissedCode:
    return MissedCode(
        code=data["code"],
        kind=data["kind"],
        description=data["description"],
        evidence=[_parse_evidence_span(e) for e in data.get("evidence", [])],
        confidence=data["confidence"],
        hcc_category=data.get("hcc_category"),
        raf_weight=data.get("raf_weight"),
        estimated_revenue=data.get("estimated_revenue"),
        hcc_model=data.get("hcc_model"),
    )


def _parse_unsupported(data: dict[str, Any]) -> UnsupportedCode:
    return UnsupportedCode(
        code=data["code"],
        kind=data["kind"],
        description=data["description"],
        reason=data["reason"],
        what_would_support_it=data["what_would_support_it"],
        radv_risk=data["radv_risk"],
        estimated_exposure=data.get("estimated_exposure"),
    )


def _parse_specificity(data: dict[str, Any]) -> SpecificityUpgrade:
    mcc = data.get("mcc_cc_change")
    return SpecificityUpgrade(
        from_code=data["from_code"],
        to_code=data["to_code"],
        from_description=data["from_description"],
        to_description=data["to_description"],
        evidence=[_parse_evidence_span(e) for e in data.get("evidence", [])],
        mcc_cc_change=(
            MCCCCChange(from_=mcc["from"], to=mcc["to"]) if mcc else None
        ),
        drg_impact=data.get("drg_impact"),
    )


def _parse_denial(data: dict[str, Any]) -> DenialRisk:
    return DenialRisk(
        code=data["code"],
        kind=data["kind"],
        description=data["description"],
        risk=data["risk"],
        probability=data["probability"],
        reasons=list(data.get("reasons", [])),
    )


def _parse_problem_list_entry(data: dict[str, Any]) -> ProblemListEntry:
    return ProblemListEntry(
        condition=data["condition"],
        icd10_code=data["icd10_code"],
        status=data["status"],
        first_seen=ProblemListDocumentRef(
            document_id=data["first_seen"]["document_id"],
            date=data["first_seen"].get("date"),
        ),
        last_seen=ProblemListDocumentRef(
            document_id=data["last_seen"]["document_id"],
            date=data["last_seen"].get("date"),
        ),
        evidence=[_parse_evidence_span(e) for e in data.get("evidence", [])],
    )


def _parse_audit_response(data: dict[str, Any]) -> AuditResponse:
    totals = AuditTotals(**data["totals"])
    rates = RatesUsed(**data["rates_used"])
    problem_list_raw = data.get("problem_list")
    hint_raw = data.get("upgrade_hint")
    return AuditResponse(
        capabilities_run=list(data["capabilities_run"]),
        confirmed=[_parse_confirmed(c) for c in data.get("confirmed", [])],
        missed=[_parse_missed(m) for m in data.get("missed", [])],
        unsupported=[_parse_unsupported(u) for u in data.get("unsupported", [])],
        specificity_upgrades=[
            _parse_specificity(s) for s in data.get("specificity_upgrades", [])
        ],
        denial_risk=[_parse_denial(d) for d in data.get("denial_risk", [])],
        totals=totals,
        provider=data["provider"],
        rates_used=rates,
        problem_list=(
            [_parse_problem_list_entry(p) for p in problem_list_raw]
            if problem_list_raw is not None
            else None
        ),
        upgrade_hint=(
            UpgradeHint(
                denied_capabilities=list(hint_raw["denied_capabilities"]),
                required_plan=hint_raw["required_plan"],
                message=hint_raw["message"],
            )
            if hint_raw is not None
            else None
        ),
    )
