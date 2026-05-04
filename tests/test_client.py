from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest

from autoicd import (
    AnonymizeResponse,
    AuditCode,
    AuditContext,
    AuditPatientContext,
    AuditRequest,
    AuditResponse,
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
    ReferenceICD10Record,
    SearchOptions,
    TranslateFrom,
    TranslateRequest,
    TranslateResponse,
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


# ── icd10.search() ──────────────────────────────────────────────────


class TestICD10CodesSearch:
    def test_sends_get_with_query(self) -> None:
        search_response = {"query": "diabetes", "count": 1, "codes": []}
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json=search_response, headers=_RATE_LIMIT_HEADERS)

        client = _make_client(httpx.MockTransport(handler))
        result = client.icd10.search("diabetes")

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
        client.icd10.search("diabetes", options=SearchOptions(limit=5))

        assert "limit=5" in str(requests[0].url)
        client.close()


# ── icd10.get() ─────────────────────────────────────────────────────


class TestReferenceLookup:
    def test_dispatches_to_reference_endpoint(self) -> None:
        payload = {
            "system": "icd-10-cm",
            "code": "I50.23",
            "record": {
                "code": "I50.23",
                "short_description": "Acute on chronic systolic CHF",
                "long_description": "Acute on chronic systolic (congestive) heart failure",
                "is_billable": True,
                "synonyms": {},
                "cross_references": {},
                "parent": None,
                "children": [],
                "chapter": None,
                "block": None,
                "icd11_mappings": [],
                "icf_categories": [],
            },
        }
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json=payload, headers=_RATE_LIMIT_HEADERS)

        client = _make_client(httpx.MockTransport(handler))
        result = client.reference.lookup("icd-10-cm", "I50.23")

        assert requests[0].method == "GET"
        assert requests[0].url.path == "/api/v1/reference/icd-10-cm/I50.23"
        assert isinstance(result, ReferenceICD10Record)
        assert result.system == "icd-10-cm"
        assert result.record.code == "I50.23"
        assert result.record.is_billable is True
        client.close()


class TestICD10CodesGet:
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
        result = client.icd10.get("E11.9")

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


_AUDIT_RESPONSE = {
    "capabilities_run": ["hcc"],
    "confirmed": [
        {
            "code": "E11.9",
            "kind": "icd10",
            "description": "Type 2 diabetes without complications",
            "evidence": [
                {"document_id": "doc_0", "start": 8, "end": 23, "quote": "type 2 diabetes"}
            ],
            "confidence": 0.97,
        }
    ],
    "missed": [
        {
            "code": "I50.9",
            "kind": "icd10",
            "description": "Heart failure, unspecified",
            "evidence": [
                {"document_id": "doc_0", "start": 28, "end": 41, "quote": "heart failure"}
            ],
            "confidence": 0.93,
            "hcc_category": "HCC85",
            "raf_weight": 0.323,
            "estimated_revenue": 4264.0,
            "hcc_model": "v22",
        }
    ],
    "unsupported": [],
    "specificity_upgrades": [],
    "denial_risk": [],
    "totals": {
        "missed_raf": 0.323,
        "estimated_revenue_recovery": 4264.0,
        "radv_exposure": 0.0,
        "drg_upside": 0.0,
        "codes_confirmed": 1,
        "codes_missed": 1,
        "codes_unsupported": 0,
        "upgrades_available": 0,
    },
    "provider": "autoicd-audit-v0.2",
    "rates_used": {
        "cms_base_rate": 13200.0,
        "hospital_base_rate": 6500.0,
        "source": "cms_national_2026",
        "hcc_model": "both",
    },
}


class TestAudit:
    def test_sends_request_and_parses(self) -> None:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["body"] = request.read().decode()
            return httpx.Response(status_code=200, json=_AUDIT_RESPONSE, headers=_RATE_LIMIT_HEADERS)

        client = _make_client(httpx.MockTransport(handler))
        result = client.audit(
            AuditRequest(
                text="pt with type 2 diabetes and heart failure",
                codes=[AuditCode(code="E11.9", kind="icd10")],
                capabilities=["hcc"],
            )
        )

        import json as _json
        body = _json.loads(captured["body"])  # type: ignore[arg-type]
        assert "/api/v1/audit" in captured["url"]  # type: ignore[operator]
        assert body["capabilities"] == ["hcc"]
        assert body["codes"][0]["code"] == "E11.9"

        assert isinstance(result, AuditResponse)
        assert result.missed[0].hcc_category == "HCC85"
        assert result.missed[0].hcc_model == "v22"
        assert result.totals.estimated_revenue_recovery == 4264.0
        client.close()

    def test_accepts_plain_dict(self) -> None:
        client = _make_client(_mock_transport(json_body=_AUDIT_RESPONSE, headers=_RATE_LIMIT_HEADERS))
        result = client.audit({
            "text": "x",
            "codes": [{"code": "E11.9", "kind": "icd10"}],
        })
        assert isinstance(result, AuditResponse)
        assert result.capabilities_run == ["hcc"]
        client.close()

    def test_context_marshalling(self) -> None:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = request.read().decode()
            return httpx.Response(status_code=200, json=_AUDIT_RESPONSE, headers=_RATE_LIMIT_HEADERS)

        client = _make_client(httpx.MockTransport(handler))
        client.audit(
            AuditRequest(
                text="x",
                codes=[AuditCode(code="E11.9", kind="icd10")],
                context=AuditContext(
                    patient=AuditPatientContext(coverage="medicare_advantage"),
                    hcc_model="v28",
                ),
            )
        )

        import json as _json
        body = _json.loads(captured["body"])  # type: ignore[arg-type]
        assert body["context"]["hcc_model"] == "v28"
        assert body["context"]["patient"]["coverage"] == "medicare_advantage"
        client.close()


_TRANSLATE_RESPONSE = {
    "from": {
        "code": "E11.9",
        "system": "icd10",
        "description": "Type 2 diabetes without complications",
    },
    "mappings": {
        "icd11": [
            {"code": "5A11", "description": "Type 2 diabetes mellitus", "mapping_type": "equivalent"}
        ],
        "snomed": [{"code": "44054006"}, {"code": "73211009"}],
        "icf": [{"code": "b540", "description": "General metabolic functions", "component": "b"}],
    },
    "unsupported_targets": [],
    "provider": "autoicd-translate-v0.1",
}


class TestTranslate:
    def test_sends_post_and_parses(self) -> None:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["body"] = request.read().decode()
            return httpx.Response(status_code=200, json=_TRANSLATE_RESPONSE, headers=_RATE_LIMIT_HEADERS)

        client = _make_client(httpx.MockTransport(handler))
        result = client.translate(TranslateRequest(from_=TranslateFrom(code="E11.9", system="icd10")))

        import json as _json
        body = _json.loads(captured["body"])  # type: ignore[arg-type]
        assert "/api/v1/translate" in captured["url"]  # type: ignore[operator]
        assert body["from"]["code"] == "E11.9"
        assert body["from"]["system"] == "icd10"
        assert "to" not in body  # optional target list omitted

        assert isinstance(result, TranslateResponse)
        assert result.from_.code == "E11.9"
        assert len(result.mappings["icd11"]) == 1
        assert result.mappings["icd11"][0].mapping_type == "equivalent"
        assert len(result.mappings["snomed"]) == 2
        assert result.mappings["icf"][0].component == "b"
        assert result.provider == "autoicd-translate-v0.1"
        client.close()

    def test_narrows_targets_via_to(self) -> None:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = request.read().decode()
            return httpx.Response(status_code=200, json=_TRANSLATE_RESPONSE, headers=_RATE_LIMIT_HEADERS)

        client = _make_client(httpx.MockTransport(handler))
        client.translate(TranslateRequest(
            from_=TranslateFrom(code="E11.9", system="icd10"),
            to=["icd11", "snomed"],
        ))
        import json as _json
        body = _json.loads(captured["body"])  # type: ignore[arg-type]
        assert body["to"] == ["icd11", "snomed"]
        client.close()

    def test_accepts_plain_dict(self) -> None:
        client = _make_client(_mock_transport(json_body=_TRANSLATE_RESPONSE, headers=_RATE_LIMIT_HEADERS))
        result = client.translate({"from": {"code": "5A11", "system": "icd11"}})
        assert isinstance(result, TranslateResponse)
        assert result.provider == "autoicd-translate-v0.1"
        client.close()


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
            client.icd10.get("ZZZZZ")
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


# ── Unified code() include flags ─────────────────────────────────────


class TestUnifiedCodeFlags:
    def test_include_flags_sent_in_body(self):
        """code() should pass include flags to the request body."""
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = request.content.decode()
            return httpx.Response(200, json=_CODING_RESPONSE, headers=_RATE_LIMIT_HEADERS)

        transport = httpx.MockTransport(handler)
        client = _make_client(transport)
        client.code("test", CodeOptions(
            include_loinc=True,
            include_icd11=True,
            include_snomed=True,
            include_umls=True,
        ))
        import json
        body = json.loads(captured["body"])
        assert body["include_loinc"] is True
        assert body["include_icd11"] is True
        assert body["include_snomed"] is True
        assert body["include_umls"] is True

    def test_loinc_entities_parsed(self):
        """loinc_entities should be parsed when present."""
        response_data = {
            **_CODING_RESPONSE,
            "loinc_entities": [
                {
                    "entity_text": "hemoglobin A1c",
                    "codes": [
                        {
                            "code": "4548-4",
                            "long_common_name": "Hemoglobin A1c",
                            "component": "Hemoglobin A1c",
                            "system": "Bld",
                            "similarity": 0.92,
                            "confidence": "high",
                            "matched_term": "hemoglobin a1c",
                        }
                    ],
                }
            ],
        }
        transport = _mock_transport(json_body=response_data, headers=_RATE_LIMIT_HEADERS)
        client = _make_client(transport)
        result = client.code("test", CodeOptions(include_loinc=True))
        assert result.loinc_entities is not None
        assert len(result.loinc_entities) == 1
        assert result.loinc_entities[0].entity_text == "hemoglobin A1c"
        assert result.loinc_entities[0].codes[0].code == "4548-4"

    def test_optional_fields_absent(self):
        """loinc_entities/icf_entities should be None when not in response."""
        transport = _mock_transport(json_body=_CODING_RESPONSE, headers=_RATE_LIMIT_HEADERS)
        client = _make_client(transport)
        result = client.code("test")
        assert result.loinc_entities is None
        assert result.icf_entities is None
