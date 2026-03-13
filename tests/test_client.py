from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest

from autoicd import (
    AnonymizeResponse,
    AuthenticationError,
    AutoICD,
    AutoICDError,
    CodeDetail,
    CodeOptions,
    CodeSearchResponse,
    ICD11CodeDetailFull,
    ICD11CodeSearchResponse,
    NotFoundError,
    RateLimitError,
    SearchOptions,
)


# ── Helpers ─────────────────────────────────────────────────────────


def _mock_transport(
    *,
    status: int = 200,
    json_body: dict | list | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.MockTransport:
    """Return an httpx MockTransport that always responds with the given values."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=status,
            json=json_body,
            headers=headers or {},
        )

    return httpx.MockTransport(handler)


def _make_client(transport: httpx.MockTransport) -> AutoICD:
    http_client = httpx.Client(transport=transport)
    return AutoICD(api_key="sk_test_123", http_client=http_client)


_RATE_LIMIT_HEADERS = {
    "X-RateLimit-Limit": "1000",
    "X-RateLimit-Remaining": "987",
    "X-RateLimit-Reset": "2026-03-12T00:00:00+00:00",
}

_CODING_RESPONSE = {
    "text": "Patient has diabetes",
    "provider": "sapbert",
    "entity_count": 1,
    "entities": [
        {
            "entity_text": "diabetes",
            "entity_start": 12,
            "entity_end": 20,
            "negated": False,
            "historical": False,
            "family_history": False,
            "uncertain": False,
            "severity": None,
            "codes": [
                {
                    "code": "E11.9",
                    "description": "Type 2 diabetes mellitus without complications",
                    "similarity": 0.92,
                    "confidence": "high",
                    "matched_term": "diabetes mellitus",
                }
            ],
        }
    ],
}


# ── Constructor ─────────────────────────────────────────────────────


class TestConstructor:
    def test_empty_api_key_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            AutoICD(api_key="")

    def test_strips_trailing_slash(self) -> None:
        transport = _mock_transport(json_body=_CODING_RESPONSE, headers=_RATE_LIMIT_HEADERS)
        client = _make_client(transport)
        client._base_url  # noqa: B018 – just checking it's accessible
        client.close()

        custom = AutoICD(
            api_key="sk_test",
            base_url="https://example.com/",
            http_client=httpx.Client(transport=transport),
        )
        assert custom._base_url == "https://example.com"
        custom.close()


# ── code() ──────────────────────────────────────────────────────────


class TestCode:
    def test_sends_correct_request(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json=_CODING_RESPONSE, headers=_RATE_LIMIT_HEADERS)

        client = _make_client(httpx.MockTransport(handler))
        result = client.code("Patient has diabetes")

        assert len(requests) == 1
        req = requests[0]
        assert req.method == "POST"
        assert req.url.path == "/api/v1/code"
        assert req.headers["authorization"] == "Bearer sk_test_123"
        assert result.text == "Patient has diabetes"
        assert len(result.entities) == 1
        assert result.entities[0].codes[0].code == "E11.9"
        client.close()

    def test_sends_options(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json=_CODING_RESPONSE, headers=_RATE_LIMIT_HEADERS)

        client = _make_client(httpx.MockTransport(handler))
        client.code(
            "test",
            options=CodeOptions(top_k=3, include_negated=False),
        )

        import json

        body = json.loads(requests[0].content)
        assert body["top_k"] == 3
        assert body["include_negated"] is False
        client.close()

    def test_omits_none_options(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json=_CODING_RESPONSE, headers=_RATE_LIMIT_HEADERS)

        client = _make_client(httpx.MockTransport(handler))
        client.code("test", options=CodeOptions(top_k=3))

        import json

        body = json.loads(requests[0].content)
        assert "top_k" in body
        assert "include_negated" not in body
        client.close()


# ── codes.search() ──────────────────────────────────────────────────


class TestCodesSearch:
    def test_sends_get_with_query(self) -> None:
        search_response = {"query": "diabetes", "count": 1, "codes": []}
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json=search_response, headers=_RATE_LIMIT_HEADERS)

        client = _make_client(httpx.MockTransport(handler))
        result = client.codes.search("diabetes")

        assert requests[0].method == "GET"
        assert "q=diabetes" in str(requests[0].url)
        assert isinstance(result, CodeSearchResponse)
        client.close()

    def test_includes_limit(self) -> None:
        search_response = {"query": "diabetes", "count": 0, "codes": []}
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json=search_response, headers=_RATE_LIMIT_HEADERS)

        client = _make_client(httpx.MockTransport(handler))
        client.codes.search("diabetes", options=SearchOptions(limit=5))

        assert "limit=5" in str(requests[0].url)
        client.close()


# ── codes.get() ─────────────────────────────────────────────────────


class TestCodesGet:
    def test_url_encodes_code(self) -> None:
        detail = {
            "code": "E11.9",
            "short_description": "Type 2 DM",
            "long_description": "Type 2 diabetes mellitus without complications",
            "is_billable": True,
        }
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json=detail, headers=_RATE_LIMIT_HEADERS)

        client = _make_client(httpx.MockTransport(handler))
        result = client.codes.get("E11.9")

        assert requests[0].method == "GET"
        assert isinstance(result, CodeDetail)
        assert result.code == "E11.9"
        assert result.is_billable is True
        client.close()


# ── icd11.search() ──────────────────────────────────────────────────


class TestICD11Search:
    def test_sends_get_with_query(self) -> None:
        search_response = {
            "query": "diabetes",
            "count": 1,
            "codes": [
                {
                    "code": "5A11",
                    "short_description": "Type 2 diabetes mellitus",
                    "long_description": "Type 2 diabetes mellitus",
                    "foundation_uri": "http://id.who.int/icd/entity/1691003785",
                }
            ],
        }
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json=search_response, headers=_RATE_LIMIT_HEADERS)

        client = _make_client(httpx.MockTransport(handler))
        result = client.icd11.search("diabetes")

        assert requests[0].method == "GET"
        assert "q=diabetes" in str(requests[0].url)
        assert "/api/v1/icd11/codes/search" in str(requests[0].url)
        assert isinstance(result, ICD11CodeSearchResponse)
        assert result.count == 1
        assert result.codes[0].code == "5A11"
        assert result.codes[0].foundation_uri == "http://id.who.int/icd/entity/1691003785"
        client.close()

    def test_includes_limit(self) -> None:
        search_response = {"query": "diabetes", "count": 0, "codes": []}
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json=search_response, headers=_RATE_LIMIT_HEADERS)

        client = _make_client(httpx.MockTransport(handler))
        client.icd11.search("diabetes", options=SearchOptions(limit=5))

        assert "limit=5" in str(requests[0].url)
        client.close()


# ── icd11.get() ─────────────────────────────────────────────────────


class TestICD11Get:
    def test_fetches_icd11_code_detail(self) -> None:
        detail = {
            "code": "5A11",
            "short_description": "Type 2 diabetes mellitus",
            "long_description": "Type 2 diabetes mellitus",
            "foundation_uri": "http://id.who.int/icd/entity/1691003785",
            "synonyms": {"index_terms": ["DM2", "NIDDM"]},
            "cross_references": {"snomed": ["44054006"], "umls": ["C0011860"]},
            "parent": {
                "code": "5A1",
                "short_description": "Diabetes mellitus",
                "long_description": "Diabetes mellitus",
                "foundation_uri": None,
            },
            "children": [],
            "chapter": {"number": 5, "title": "Endocrine, nutritional or metabolic diseases"},
            "block": "5A10-5A14",
            "icd10_mappings": [
                {
                    "code": "E11.9",
                    "description": "Type 2 diabetes mellitus without complications",
                    "mapping_type": "equivalent",
                    "system": "icd10",
                }
            ],
        }
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json=detail, headers=_RATE_LIMIT_HEADERS)

        client = _make_client(httpx.MockTransport(handler))
        result = client.icd11.get("5A11")

        assert requests[0].method == "GET"
        assert "/api/v1/icd11/codes/5A11" in str(requests[0].url)
        assert isinstance(result, ICD11CodeDetailFull)
        assert result.code == "5A11"
        assert result.foundation_uri == "http://id.who.int/icd/entity/1691003785"
        assert result.parent is not None
        assert result.parent.code == "5A1"
        assert result.chapter is not None
        assert result.chapter.number == 5
        assert len(result.icd10_mappings) == 1
        assert result.icd10_mappings[0].code == "E11.9"
        assert result.icd10_mappings[0].mapping_type == "equivalent"
        assert result.cross_references == {"snomed": ["44054006"], "umls": ["C0011860"]}
        client.close()

    def test_404_raises_not_found(self) -> None:
        client = _make_client(
            _mock_transport(status=404, json_body={"error": "Code not found"})
        )
        with pytest.raises(NotFoundError) as exc:
            client.icd11.get("INVALID")
        assert exc.value.status == 404
        client.close()


# ── anonymize() ─────────────────────────────────────────────────────


class TestAnonymize:
    def test_sends_post_and_parses(self) -> None:
        response = {
            "original_text": "John Smith has COPD",
            "anonymized_text": "[NAME] has COPD",
            "pii_count": 1,
            "pii_entities": [
                {
                    "text": "John Smith",
                    "start": 0,
                    "end": 10,
                    "label": "NAME",
                    "replacement": "[NAME]",
                }
            ],
        }

        client = _make_client(_mock_transport(json_body=response, headers=_RATE_LIMIT_HEADERS))
        result = client.anonymize("John Smith has COPD")

        assert isinstance(result, AnonymizeResponse)
        assert result.anonymized_text == "[NAME] has COPD"
        assert result.pii_entities[0].label == "NAME"
        client.close()


# ── Error handling ──────────────────────────────────────────────────


class TestErrors:
    def test_401_raises_authentication_error(self) -> None:
        client = _make_client(
            _mock_transport(status=401, json_body={"error": "Invalid API key"})
        )
        with pytest.raises(AuthenticationError) as exc:
            client.code("test")
        assert exc.value.status == 401
        client.close()

    def test_404_raises_not_found_error(self) -> None:
        client = _make_client(
            _mock_transport(status=404, json_body={"error": "Code not found"})
        )
        with pytest.raises(NotFoundError) as exc:
            client.codes.get("ZZZZZ")
        assert exc.value.status == 404
        client.close()

    def test_429_raises_rate_limit_error(self) -> None:
        client = _make_client(
            _mock_transport(
                status=429,
                json_body={"error": "Rate limit exceeded"},
                headers=_RATE_LIMIT_HEADERS,
            )
        )
        with pytest.raises(RateLimitError) as exc:
            client.code("test")
        assert exc.value.status == 429
        assert exc.value.rate_limit.limit == 1000
        client.close()

    def test_500_raises_generic_error(self) -> None:
        client = _make_client(
            _mock_transport(status=500, json_body={"error": "Internal server error"})
        )
        with pytest.raises(AutoICDError) as exc:
            client.code("test")
        assert exc.value.status == 500
        client.close()


# ── Rate limit parsing ──────────────────────────────────────────────


class TestRateLimit:
    def test_parses_headers(self) -> None:
        client = _make_client(
            _mock_transport(json_body=_CODING_RESPONSE, headers=_RATE_LIMIT_HEADERS)
        )
        client.code("test")

        assert client.last_rate_limit is not None
        assert client.last_rate_limit.limit == 1000
        assert client.last_rate_limit.remaining == 987
        assert isinstance(client.last_rate_limit.reset_at, datetime)
        client.close()

    def test_none_when_headers_missing(self) -> None:
        client = _make_client(_mock_transport(json_body=_CODING_RESPONSE))
        client.code("test")

        assert client.last_rate_limit is None
        client.close()
