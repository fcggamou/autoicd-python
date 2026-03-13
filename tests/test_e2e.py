"""E2E sync tests — hit the live API and validate response shapes match SDK types.

These tests catch drift between the API and SDK types. They use the test
API key from the monorepo CLAUDE.md and run against production.

Run with:  AUTOICD_E2E=1 AUTOICD_TEST_API_KEY=sk_... pytest tests/test_e2e.py -v
Skip with: pytest  (skipped by default)
"""

from __future__ import annotations

import os

import pytest

from autoicd import (
    AnonymizeResponse,
    AutoICD,
    ChapterInfo,
    CodeDetail,
    CodeDetailFull,
    CodeMatch,
    CodeSearchResponse,
    CodingEntity,
    CodingResponse,
    PIIEntity,
)

API_KEY = os.environ.get("AUTOICD_TEST_API_KEY", "")
RUN_E2E = os.environ.get("AUTOICD_E2E") == "1"

pytestmark = pytest.mark.skipif(not RUN_E2E, reason="Set AUTOICD_E2E=1 to run E2E tests")


# ── Helpers ──────────────────────────────────────────────────────────


def assert_code_match(match: CodeMatch) -> None:
    assert isinstance(match.code, str) and len(match.code) > 0
    assert isinstance(match.description, str)
    assert isinstance(match.similarity, (int, float))
    assert 0 <= match.similarity <= 1.01
    assert match.confidence in ("high", "moderate")
    assert isinstance(match.matched_term, str)


def assert_coding_entity(entity: CodingEntity) -> None:
    assert isinstance(entity.entity_text, str)
    assert isinstance(entity.entity_start, int)
    assert isinstance(entity.entity_end, int)
    assert isinstance(entity.negated, bool)
    assert isinstance(entity.historical, bool)
    assert isinstance(entity.family_history, bool)
    assert isinstance(entity.uncertain, bool)
    assert entity.severity is None or isinstance(entity.severity, str)
    assert isinstance(entity.codes, list)
    for code in entity.codes:
        assert_code_match(code)
    # merged_from: None or list[str]
    if entity.merged_from is not None:
        assert isinstance(entity.merged_from, list)
        for item in entity.merged_from:
            assert isinstance(item, str)
    # corrected_from: None or str
    if entity.corrected_from is not None:
        assert isinstance(entity.corrected_from, str)


def assert_code_detail(detail: CodeDetail) -> None:
    assert isinstance(detail.code, str)
    assert isinstance(detail.short_description, str)
    assert isinstance(detail.long_description, str)
    assert isinstance(detail.is_billable, bool)


def assert_chapter_info(chapter: ChapterInfo) -> None:
    assert isinstance(chapter.number, int)
    assert 1 <= chapter.number <= 22
    assert isinstance(chapter.range, str)
    assert isinstance(chapter.title, str)


def assert_code_detail_full(detail: CodeDetailFull) -> None:
    assert_code_detail(detail)

    # synonyms: dict[str, list[str]]
    assert isinstance(detail.synonyms, dict)
    for source, terms in detail.synonyms.items():
        assert isinstance(source, str)
        assert isinstance(terms, list)
        for term in terms:
            assert isinstance(term, str)

    # cross_references: dict[str, list[str]]
    assert isinstance(detail.cross_references, dict)
    for source, ids in detail.cross_references.items():
        assert isinstance(source, str)
        assert isinstance(ids, list)
        for ref_id in ids:
            assert isinstance(ref_id, str)

    # parent: CodeDetail | None
    if detail.parent is not None:
        assert_code_detail(detail.parent)

    # children: list[CodeDetail]
    assert isinstance(detail.children, list)
    for child in detail.children:
        assert_code_detail(child)

    # chapter: ChapterInfo | None
    if detail.chapter is not None:
        assert_chapter_info(detail.chapter)

    # block: str | None
    assert detail.block is None or isinstance(detail.block, str)


def assert_pii_entity(entity: PIIEntity) -> None:
    assert isinstance(entity.text, str)
    assert isinstance(entity.start, int)
    assert isinstance(entity.end, int)
    assert isinstance(entity.label, str)
    assert entity.label in ("NAME", "DATE", "SSN", "PHONE", "EMAIL", "ADDRESS", "MRN", "AGE")
    assert isinstance(entity.replacement, str)


# ── Tests ────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def client() -> AutoICD:
    return AutoICD(api_key=API_KEY, timeout=60.0)


class TestCodeEndpoint:
    def test_response_matches_coding_response_shape(self, client: AutoICD) -> None:
        result = client.code(
            "Patient presents with type 2 diabetes and essential hypertension. "
            "No evidence of heart failure.",
            options=None,
        )

        assert isinstance(result, CodingResponse)
        assert isinstance(result.text, str)
        assert isinstance(result.provider, str)
        assert isinstance(result.entity_count, int)
        assert result.entity_count > 0
        assert isinstance(result.entities, list)
        assert len(result.entities) == result.entity_count

        for entity in result.entities:
            assert_coding_entity(entity)

        # Verify we got real codes back
        all_codes = [c.code for e in result.entities for c in e.codes]
        assert len(all_codes) > 0

        # Should detect negation for "heart failure"
        negated = [e for e in result.entities if e.negated]
        assert len(negated) > 0

    def test_no_unexpected_fields_in_response(self, client: AutoICD) -> None:
        """Catch new API fields that aren't in the SDK types yet."""
        # Make a raw HTTP request to check field names
        import httpx

        raw = httpx.post(
            "https://autoicdapi.com/api/v1/code",
            json={"text": "Patient has asthma", "top_k": 1},
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=60.0,
        )
        data = raw.json()

        allowed_top = {"text", "provider", "entity_count", "entities"}
        assert set(data.keys()) <= allowed_top, f"Unexpected top-level fields: {set(data.keys()) - allowed_top}"

        allowed_entity = {
            "entity_text", "entity_start", "entity_end",
            "negated", "historical", "family_history", "uncertain", "severity",
            "codes", "merged_from", "corrected_from",
        }
        for entity in data["entities"]:
            assert set(entity.keys()) <= allowed_entity, f"Unexpected entity fields: {set(entity.keys()) - allowed_entity}"

        allowed_code = {"code", "description", "similarity", "confidence", "matched_term"}
        for entity in data["entities"]:
            for code in entity["codes"]:
                assert set(code.keys()) <= allowed_code, f"Unexpected code fields: {set(code.keys()) - allowed_code}"


class TestAnonymizeEndpoint:
    def test_response_matches_anonymize_response_shape(self, client: AutoICD) -> None:
        result = client.anonymize(
            "John Smith, DOB 03/15/1980, was seen at 123 Main St "
            "for chronic obstructive pulmonary disease."
        )

        assert isinstance(result, AnonymizeResponse)
        assert isinstance(result.original_text, str)
        assert isinstance(result.anonymized_text, str)
        assert isinstance(result.pii_count, int)
        assert result.pii_count > 0
        assert isinstance(result.pii_entities, list)

        for entity in result.pii_entities:
            assert_pii_entity(entity)

        # Anonymized text should contain replacement tokens
        assert "[" in result.anonymized_text


class TestCodesSearchEndpoint:
    def test_response_matches_search_response_shape(self, client: AutoICD) -> None:
        from autoicd import SearchOptions

        result = client.icd10.search("diabetes", options=SearchOptions(limit=5))

        assert isinstance(result, CodeSearchResponse)
        assert result.query == "diabetes"
        assert isinstance(result.count, int)
        assert result.count > 0
        assert isinstance(result.codes, list)
        assert len(result.codes) <= 5

        for code in result.codes:
            assert_code_detail(code)


class TestCodesGetEndpoint:
    def test_response_matches_code_detail_full_shape(self, client: AutoICD) -> None:
        result = client.icd10.get("E11.9")

        assert isinstance(result, CodeDetailFull)
        assert_code_detail_full(result)

        # Specific expectations for E11.9
        assert result.code == "E11.9"
        assert result.is_billable is True
        assert result.chapter is not None
        assert result.parent is not None

        # Must have cross_references (this caught the OpenAPI spec drift)
        assert isinstance(result.cross_references, dict)

        # Must have synonyms
        assert len(result.synonyms) > 0

    def test_no_unexpected_fields_in_code_detail(self, client: AutoICD) -> None:
        """Catch new API fields that aren't in the SDK types yet."""
        import httpx

        raw = httpx.get(
            "https://autoicdapi.com/api/v1/icd10/codes/I10",
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=60.0,
        )
        data = raw.json()

        allowed = {
            "code", "short_description", "long_description", "is_billable",
            "synonyms", "cross_references", "parent", "children", "chapter", "block",
            "icd11_mappings",
        }
        assert set(data.keys()) <= allowed, f"Unexpected fields: {set(data.keys()) - allowed}"


class TestRateLimitParsing:
    def test_rate_limit_headers_are_parsed(self, client: AutoICD) -> None:
        from autoicd import SearchOptions

        client.icd10.search("test", options=SearchOptions(limit=1))

        assert client.last_rate_limit is not None
        assert isinstance(client.last_rate_limit.limit, int)
        assert isinstance(client.last_rate_limit.remaining, int)
        from datetime import datetime

        assert isinstance(client.last_rate_limit.reset_at, datetime)
