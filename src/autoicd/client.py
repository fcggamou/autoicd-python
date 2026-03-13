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
    PIIEntity,
    SearchOptions,
)

_DEFAULT_BASE_URL = "https://autoicdapi.com"
_DEFAULT_TIMEOUT = 30.0


class Codes:
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
        data = self._client._get(f"/api/v1/codes/search?{urlencode(params)}")
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
        data = self._client._get(f"/api/v1/codes/{quote(code, safe='')}")
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
        self.codes = Codes(self)
        self.icd11 = ICD11Codes(self)
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
    return CodingResponse(
        text=data["text"],
        provider=data["provider"],
        entity_count=data["entity_count"],
        entities=[_parse_entity(e) for e in data.get("entities", [])],
    )


def _parse_crosswalk_mappings(data: list[dict[str, Any]]) -> list[CrosswalkMapping]:
    return [CrosswalkMapping(**m) for m in data]


def _parse_code_detail_full(data: dict[str, Any]) -> CodeDetailFull:
    parent_data = data.get("parent")
    parent = CodeDetail(**parent_data) if parent_data else None

    children = [CodeDetail(**c) for c in data.get("children", [])]

    chapter_data = data.get("chapter")
    chapter = ChapterInfo(**chapter_data) if chapter_data else None

    icd11_raw = data.get("icd11_mappings")
    icd11_mappings = _parse_crosswalk_mappings(icd11_raw) if icd11_raw else None

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
    )
