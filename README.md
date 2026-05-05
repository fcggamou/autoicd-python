# AutoICD API — Python SDK

[![PyPI version](https://img.shields.io/pypi/v/autoicd.svg)](https://pypi.org/project/autoicd/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)

Official Python SDK for the [AutoICD API](https://autoicdapi.com) — AI medical coding that converts clinical text to ICD-10-CM, ICD-11, and ICF codes using medical NLP. Automate ICD-10 coding, ICF functioning classification, and disability assessment in your application.

Single dependency (`httpx`). Works in **Python 3.10+**.

> Built for EHR integrations, health-tech platforms, medical billing, clinical decision support, and revenue cycle management.

---

## What's new — 2026-05-05

- **Phase 3 unified reference lookup.** A single `client.reference.lookup(system, code)` covers ICD-10-CM, ICD-11, ICF, LOINC, SNOMED CT, UMLS, and RxNorm. The legacy per-system getters (`icd10.get`, `icd11.get`, `icf.lookup`, `loinc.lookup`) keep working but the underlying routes now emit `Deprecation` and `Sunset` headers.
- **Phase 4 SNOMED CT, UMLS, and RxNorm coverage.** Lookup canonical concept records (preferred terms, synonyms, semantic types) and search those vocabularies via `client.reference.search(system, query)`.
- **Cross-references everywhere.** ICD-10, ICD-11, LOINC, SNOMED, UMLS, and RxNorm records all carry `cross_references` keyed by target system, so you can pivot between vocabularies without extra calls.

---

## Why AutoICD API

| | |
|---|---|
| **AI-Powered ICD-10, ICD-11 & ICF Coding** | Clinical NLP extracts diagnoses from free-text notes and maps them to ICD-10-CM, ICD-11, or ICF codes — no manual lookup required |
| **Chart Audit with HCC Gap Capture** | Find missed HCCs, unsupported codes, and specificity upgrades with RAF-weighted revenue estimates (CMS v22 + v28 PY2026). Every finding carries evidence spans |
| **Cross-Standard Code Translation** | Map a code between ICD-10, ICD-11, SNOMED CT, UMLS, and ICF in one call. Forward ICD-10 → all other systems, plus reverse ICD-11 → ICD-10 and ICF → ICD-10 |
| **74,000+ ICD-10-CM Codes** | Full 2025 code set enriched with SNOMED CT synonyms for comprehensive matching |
| **ICD-11 Support** | Search and look up ICD-11 codes, with full ICD-10 ↔ ICD-11 crosswalk mappings |
| **ICF Functioning Codes** | Code clinical text to WHO ICF categories, search 1,400+ codes, and access Core Sets for 12+ conditions |
| **Negation & Context Detection** | Knows the difference between "patient has diabetes" and "patient denies diabetes" — flags negated, historical, uncertain, and family-history mentions |
| **PHI De-identification** | HIPAA-compliant anonymization of names, dates, SSNs, phone numbers, emails, addresses, MRNs, and ages |
| **Confidence Scoring** | Every code match includes a similarity score and confidence level so you can set your own acceptance thresholds |
| **Spell Correction** | Handles misspellings in clinical text — "diabeties" still maps to the right code |
| **Fully Typed** | Complete type annotations for all requests and responses |

---

## Install

```bash
pip install autoicd
```

<details>
<summary>uv / poetry / pdm</summary>

```bash
uv add autoicd
poetry add autoicd
pdm add autoicd
```

</details>

---

## Quick Start

```python
from autoicd import AutoICD

client = AutoICD(api_key="sk_...")

result = client.code(
    "Patient has type 2 diabetes and essential hypertension"
)

for entity in result.entities:
    print(entity.entity_text, "→", entity.codes[0].code)
# "type 2 diabetes"       → "E11.9"
# "essential hypertension" → "I10"
```

---

## Features

### Chart Audit (HCC gap capture, RADV defense, specificity, denial risk)

Audit a chart to surface coding gaps, unsupported codes, specificity upgrades, and denial-risk flags in one call. Every finding carries extractive evidence spans. HCC gaps include RAF-weighted revenue estimates using the CMS PY2026 V22 and V28 community models.

```python
from autoicd import AutoICD, AuditRequest, AuditCode, AuditContext, AuditPatientContext

client = AutoICD(api_key="sk_...")

audit = client.audit(AuditRequest(
    text=(
        "68yo M, type 2 diabetes stable on metformin, chronic systolic heart failure "
        "on furosemide, edema controlled. A1c 7.4 today."
    ),
    codes=[AuditCode(code="E11.9", kind="icd10")],
    capabilities=["hcc", "radv", "specificity", "denial", "problem_list"],
    context=AuditContext(
        patient=AuditPatientContext(coverage="medicare_advantage"),
        hcc_model="both",
    ),
))

print(f"Missed revenue: ${audit.totals.estimated_revenue_recovery:.0f}")
print(f"RADV exposure:  ${audit.totals.radv_exposure:.0f}")

for m in audit.missed:
    cat = m.hcc_category or "non-HCC"
    model = m.hcc_model or ""
    print(f"MISSED {m.code} ({cat} {model}) -> ${m.estimated_revenue or 0:.0f}: {m.description}")
    for span in m.evidence:
        print(f'    evidence: "{span.quote}" [{span.start}-{span.end}]')
```

| Capability | What it surfaces |
|---|---|
| `hcc` | Missed HCC codes with `hcc_category`, `raf_weight`, `estimated_revenue` per v22/v28 model |
| `radv` | Submitted codes with no supporting documentation, with `what_would_support_it` guidance and exposure dollars |
| `specificity` | Upgrade opportunities from unspecified to more specific child codes |
| `denial` | Documentation-quality risk flags (missing laterality, missing duration, age/sex mismatches) |
| `problem_list` | Deduplicated active-conditions list with status (active/historical) and evidence |

Default behavior runs all five capabilities. Pass `capabilities=["hcc"]` to run a targeted audit. The Audit endpoint also accepts plain dicts if you prefer not to import the dataclasses.

> **`hcc_model`:** use `"v22"`, `"v28"`, or `"both"` (default). CMS PY2026 MA payment uses V22 and V28 as the two main community models. V24 is the ESRD-specific model and is not accepted here.

Read more about the Audit endpoint at [autoicdapi.com/audit](https://autoicdapi.com/audit).

### Unified Reference Lookup (ICD-10, ICD-11, ICF, LOINC, SNOMED, UMLS, RxNorm)

One call to fetch canonical record data for any code in any supported system. The response is a tagged dataclass — switch on `result.system` to access the system-specific shape.

```python
icd10 = client.reference.lookup("icd-10-cm", "E11.9")
print(icd10.record.long_description)
print(icd10.record.cross_references)  # {"snomed": [...], "umls": [...], "rxnorm": [...]}

concept = client.reference.lookup("snomed-ct", "44054006")
print(concept.record.preferred_term)  # "Diabetes mellitus type 2"
print(concept.record.semantic_tag)    # "disorder"

cui = client.reference.lookup("umls", "C0011860")
print(cui.record.preferred_name)
print(cui.record.cross_references["snomed"])

drug = client.reference.lookup("rxnorm", "860975")  # metformin 500 MG
print(drug.record.name, drug.record.tty)
```

Supported `system` values: `"icd-10-cm"`, `"icd-11"`, `"icf"`, `"loinc"`, `"snomed-ct"`, `"umls"`, `"rxnorm"`.

### Reference Search (SNOMED CT, UMLS, RxNorm)

Free-text search the Neon-backed reference vocabularies. ICD-10, ICD-11, ICF, and LOINC keep their per-system search endpoints.

```python
hits = client.reference.search("snomed-ct", "type 2 diabetes", limit=5)
for hit in hits.results:
    print(hit.code, hit.label, hit.meta)
    # 44054006 "Diabetes mellitus type 2 (disorder)" "disorder"

cuis = client.reference.search("umls", "metformin")
drugs = client.reference.search("rxnorm", "lisinopril 10 mg", limit=10)
```

### Cross-Standard Code Translation

Translate a code between healthcare coding systems in one call. Forward from ICD-10 to ICD-11, SNOMED CT, UMLS, and ICF, plus reverse ICD-11 → ICD-10 and ICF → ICD-10. Built on CMS-published crosswalks, code-level SNOMED / UMLS concept IDs, and WHO ICF Core Sets.

```python
from autoicd import AutoICD, TranslateRequest, TranslateFrom

client = AutoICD(api_key="sk_...")

result = client.translate(TranslateRequest(
    from_=TranslateFrom(code="E11.9", system="icd10"),
))

print(result.mappings["icd11"])
# [TranslateMapping(code="5A11", description="Type 2 diabetes mellitus", mapping_type="equivalent", ...)]
print(result.mappings["snomed"])
# [TranslateMapping(code="44054006", ...), TranslateMapping(code="73211009", ...)]
print(result.mappings["icf"])
# [TranslateMapping(code="b540", description="General metabolic functions", component="b", ...)]
```

Narrow the targets when you only need specific systems:

```python
result = client.translate(TranslateRequest(
    from_=TranslateFrom(code="I50.9", system="icd10"),
    to=["icd11"],
))
```

Requested systems that aren't reachable from the source are returned in `unsupported_targets` rather than raising, so clients can request a broad target list and use whatever comes back. Plain dicts are accepted too: `client.translate({"from": {"code": "E11.9", "system": "icd10"}})`.

| From | To | Source |
|------|----|--------|
| ICD-10-CM | ICD-11, SNOMED, UMLS, ICF | CMS crosswalk + concept refsets + WHO Core Sets |
| ICD-11 MMS | ICD-10-CM | Reverse CMS crosswalk |
| ICF | ICD-10-CM | Reverse WHO ICF Core Set index |

Read more about the Translate endpoint at [autoicdapi.com/interop](https://autoicdapi.com/interop).

### Automated ICD-10 Medical Coding

Extract diagnosis entities from clinical notes and map them to ICD-10-CM codes. Each entity includes ranked candidates with confidence scores, negation status, and context flags.

```python
result = client.code(
    "History of severe COPD with acute exacerbation. Patient denies chest pain."
)

for entity in result.entities:
    print(entity.entity_text)
    print(f"  Negated: {entity.negated}")
    print(f"  Historical: {entity.historical}")
    for match in entity.codes:
        print(
            f"  {match.code} — {match.description} "
            f"({match.confidence}, {match.similarity * 100:.1f}%)"
        )
```

Fine-tune results with coding options:

```python
from autoicd import CodeOptions

result = client.code(
    "Patient presents with acute bronchitis and chest pain",
    options=CodeOptions(
        top_k=3,               # Top 3 ICD-10 candidates per entity (default: 5)
        include_negated=False, # Exclude negated conditions from results
    ),
)
```

### ICD-10 Code Search

Search the full ICD-10-CM 2025 code set by description. Perfect for building code lookup UIs, autocomplete fields, and validation workflows.

```python
results = client.icd10.search("diabetes mellitus")
# results.codes → [CodeDetail(code="E11.9", short_description="...", ...), ...]

from autoicd import SearchOptions
results = client.icd10.search("heart failure", options=SearchOptions(limit=5))
```

### ICD-10 Code Details

Get full details for any ICD-10-CM code — descriptions, billable status, synonyms, hierarchy, and chapter classification.

```python
detail = client.icd10.get("E11.9")
print(detail.code)              # "E11.9"
print(detail.long_description)  # "Type 2 diabetes mellitus without complications"
print(detail.is_billable)       # True
print(detail.synonyms["snomed"])  # ["Diabetes mellitus type 2", ...]
print(detail.chapter.title)       # "Endocrine, Nutritional and Metabolic Diseases"
```

### ICD-11 Code Search

Search the ICD-11 code set by description. The AutoICD API includes the full WHO ICD-11 MMS hierarchy.

```python
results = client.icd11.search("diabetes mellitus")
# results.codes → [ICD11CodeSearchResult(code="5A11", short_description="...", ...), ...]

results = client.icd11.search("heart failure", options=SearchOptions(limit=5))
```

### ICD-11 Code Details & Crosswalk

Get full details for any ICD-11 code — descriptions, Foundation URI, hierarchy, synonyms, and ICD-10 crosswalk mappings.

```python
detail = client.icd11.get("5A11")
print(detail.code)              # "5A11"
print(detail.short_description) # "Type 2 diabetes mellitus"
print(detail.foundation_uri)    # "http://id.who.int/icd/entity/1691003785"
print(detail.chapter.title)     # "Endocrine, nutritional or metabolic diseases"

# ICD-10 crosswalk
for mapping in detail.icd10_mappings:
    print(f"{mapping.code} — {mapping.description} ({mapping.mapping_type})")
    # "E11.9 — Type 2 diabetes mellitus without complications (equivalent)"
```

### ICD-10 → ICD-11 Crosswalk

ICD-10 code details now include ICD-11 crosswalk mappings when available:

```python
detail = client.icd10.get("E11.9")
for mapping in detail.icd11_mappings:
    print(f"{mapping.code} — {mapping.description}")
    # "5A11 — Type 2 diabetes mellitus"
```

### ICF Functioning Codes

Look up WHO ICF categories, search the catalog, and access ICF Core Sets for 12+ conditions. To extract ICF functioning categories from clinical text, pass `CodeOptions(include_icf=True)` to `client.code()`; the response carries `icf_entities` alongside the ICD-10 results.

```python
from autoicd import CodeOptions

# Extract ICF functioning categories during ICD-10 coding
result = client.code(
    "Patient with stroke and hemiplegia",
    CodeOptions(include_icf=True),
)
for entity in result.icf_entities or []:
    print(entity.entity_text, entity.codes[0].code)
    # "hemiplegia" "b730"

# Look up an ICF code
code = client.icf.lookup("d450")
print(code.title)  # "Walking"

# Search ICF codes
results = client.icf.search("mobility")

# Get ICF Core Set for a diagnosis
core_set = client.icf.core_set("E11.9")
print(core_set.condition_name)  # "Diabetes Mellitus"
```

### PHI De-identification

Strip protected health information from clinical notes before storage or analysis. HIPAA-compliant de-identification for names, dates, SSNs, phone numbers, emails, addresses, MRNs, and ages.

```python
result = client.anonymize(
    "John Smith, DOB 01/15/1980, MRN 123456, has COPD"
)

print(result.anonymized_text)
# "[NAME], DOB [DATE], MRN [MRN], has COPD"

print(result.pii_count)     # 3
print(result.pii_entities)  # [PIIEntity(text="John Smith", label="NAME", ...), ...]
```

---

## Common ICD-10 Codes

The SDK can code any of the 74,000+ ICD-10-CM codes. Here are some of the most commonly coded conditions:

| Condition | ICD-10 Code | Description |
|-----------|-------------|-------------|
| [Hypertension](https://autoicdapi.com/reference/icd-10/condition/hypertension) | [I10](https://autoicdapi.com/reference/icd-10/I10) | Essential (primary) hypertension |
| [Type 2 Diabetes](https://autoicdapi.com/reference/icd-10/condition/diabetes) | [E11.9](https://autoicdapi.com/reference/icd-10/E11.9) | Type 2 diabetes mellitus without complications |
| [Depression](https://autoicdapi.com/reference/icd-10/condition/depression) | [F32.9](https://autoicdapi.com/reference/icd-10/F32.9) | Major depressive disorder, single episode, unspecified |
| [Anxiety](https://autoicdapi.com/reference/icd-10/condition/anxiety) | [F41.1](https://autoicdapi.com/reference/icd-10/F41.1) | Generalized anxiety disorder |
| [Low Back Pain](https://autoicdapi.com/reference/icd-10/condition/back-pain) | [M54.5](https://autoicdapi.com/reference/icd-10/M54.5) | Low back pain |
| [COPD](https://autoicdapi.com/reference/icd-10/condition/copd) | [J44.9](https://autoicdapi.com/reference/icd-10/J44.9) | Chronic obstructive pulmonary disease, unspecified |
| [Heart Failure](https://autoicdapi.com/reference/icd-10/condition/heart-failure) | [I50.9](https://autoicdapi.com/reference/icd-10/I50.9) | Heart failure, unspecified |
| [UTI](https://autoicdapi.com/reference/icd-10/condition/urinary-tract-infection) | [N39.0](https://autoicdapi.com/reference/icd-10/N39.0) | Urinary tract infection, site not specified |
| [Pneumonia](https://autoicdapi.com/reference/icd-10/condition/pneumonia) | [J18.9](https://autoicdapi.com/reference/icd-10/J18.9) | Pneumonia, unspecified organism |
| [Atrial Fibrillation](https://autoicdapi.com/reference/icd-10/condition/atrial-fibrillation) | [I48.91](https://autoicdapi.com/reference/icd-10/I48.91) | Unspecified atrial fibrillation |
| [Obesity](https://autoicdapi.com/reference/icd-10/condition/obesity) | [E66.01](https://autoicdapi.com/reference/icd-10/E66.01) | Morbid (severe) obesity due to excess calories |
| [GERD](https://autoicdapi.com/reference/icd-10/condition/gerd) | [K21.9](https://autoicdapi.com/reference/icd-10/K21.9) | Gastro-esophageal reflux disease without esophagitis |
| [Hypothyroidism](https://autoicdapi.com/reference/icd-10/condition/hypothyroidism) | [E03.9](https://autoicdapi.com/reference/icd-10/E03.9) | Hypothyroidism, unspecified |
| [CKD](https://autoicdapi.com/reference/icd-10/condition/chronic-kidney-disease) | [N18.9](https://autoicdapi.com/reference/icd-10/N18.9) | Chronic kidney disease, unspecified |

Browse all 74,000+ codes in the [ICD-10-CM Code Directory](https://autoicdapi.com/reference/icd-10) or find codes by [condition](https://autoicdapi.com/reference/icd-10/condition).

---

## Use Cases

- **EHR / EMR Integration** — Auto-code clinical notes as providers type, reducing manual coding burden
- **Medical Billing & RCM** — Accelerate claim submission with accurate ICD-10 codes
- **Clinical Decision Support** — Map patient conditions to standardized codes for analytics and alerts
- **Health-Tech SaaS** — Add ICD-10 coding to your platform without building ML infrastructure
- **Clinical Research** — Extract and standardize diagnoses from unstructured medical records
- **Insurance & Payer Systems** — Validate and suggest diagnosis codes during claims processing
- **Telehealth Platforms** — Generate diagnosis codes from visit notes and transcriptions

---

## Error Handling

```python
from autoicd import (
    AutoICD,
    AuthenticationError,
    RateLimitError,
    NotFoundError,
)

try:
    result = client.code("...")
except AuthenticationError:
    # Invalid or revoked API key (401)
    ...
except RateLimitError as e:
    # Request limit exceeded (429)
    print(e.rate_limit.remaining, e.rate_limit.reset_at)
except NotFoundError:
    # ICD-10 code not found (404)
    ...
```

Rate limit info is available after every request:

```python
client.code("...")
print(client.last_rate_limit)
# RateLimit(limit=1000, remaining=987, reset_at=datetime(...))
```

---

## Configuration

```python
client = AutoICD(
    api_key="sk_...",                   # Required — get yours at https://autoicdapi.com
    base_url="https://...",             # Default: https://autoicdapi.com
    timeout=60.0,                       # Default: 30.0 seconds
    http_client=httpx.Client(...),      # Custom httpx client (for proxies, mTLS, etc.)
)
```

Use as a context manager for automatic cleanup:

```python
with AutoICD(api_key="sk_...") as client:
    result = client.code("Patient has diabetes")
```

---

## API Reference

Full REST API documentation at [autoicdapi.com/docs](https://autoicdapi.com/docs).

| Method | Description |
|--------|-------------|
| `client.code(text, options=None)` | Code clinical text to ICD-10-CM diagnoses |
| `client.audit(request)` | Chart audit (HCC gap capture, RADV, specificity, denial, problem list) |
| `client.translate(request)` | Cross-standard code translation across ICD-10, ICD-11, SNOMED, UMLS, ICF |
| `client.anonymize(text)` | De-identify PHI/PII in clinical text |
| `client.reference.lookup(system, code)` | Unified lookup across ICD-10-CM, ICD-11, ICF, LOINC, SNOMED CT, UMLS, RxNorm |
| `client.reference.search(system, query, limit=20)` | Free-text search of SNOMED CT, UMLS, or RxNorm |
| `client.icd10.search(query, options=None)` | Search ICD-10-CM codes by description |
| `client.icd10.get(code)` | Get details for an ICD-10-CM code (deprecated — use `reference.lookup`) |
| `client.icd11.search(query, options=None)` | Search ICD-11 codes by description |
| `client.icd11.get(code)` | Get details for an ICD-11 code (deprecated — use `reference.lookup`) |
| `client.icf.lookup(code)` | Get details for an ICF code (deprecated — use `reference.lookup`) |
| `client.icf.search(query, limit=20)` | Search ICF codes by keyword |
| `client.icf.core_set(icd10_code)` | Get ICF Core Set for an ICD-10 diagnosis |
| `client.loinc.code(text, top_k=5)` | Code clinical text to LOINC lab/observation codes |
| `client.loinc.lookup(code)` | Get details for a LOINC code (deprecated — use `reference.lookup`) |
| `client.loinc.search(query, limit=20)` | Search LOINC codes by description |

---

## Types

All request and response types are exported:

```python
from autoicd import (
    CodingResponse,
    CodingEntity,
    CodeMatch,
    CodeOptions,
    CodeDetail,
    CodeSearchResponse,
    AnonymizeResponse,
    PIIEntity,
    RateLimit,
    SearchOptions,
    ICD11CodeDetail,
    ICD11CodeDetailFull,
    ICD11CodeSearchResponse,
    CrosswalkMapping,
    ICFCodeDetail,
    ICFCodeSearchResponse,
    ICFCoreSetResponse,
)
```

---

## Requirements

- **Python 3.10+**
- An API key from [autoicdapi.com](https://autoicdapi.com)

---

## Links

- [AutoICD API](https://autoicdapi.com) — Homepage and API key management
- [API Documentation](https://autoicdapi.com/docs) — Full REST API reference
- [ICD-10-CM Code Directory](https://autoicdapi.com/reference/icd-10) — Browse all 74,000+ diagnosis codes
- [ICD-11 Code Directory](https://autoicdapi.com/reference/icd-11) — Browse the WHO ICD-11 MMS hierarchy
- [ICD-10 ↔ ICD-11 Crosswalk](https://autoicdapi.com/icd10-to-icd11) — Map codes between revisions
- [ICD-10 Codes by Condition](https://autoicdapi.com/reference/icd-10/condition) — Find codes for common conditions
- [TypeScript SDK](https://www.npmjs.com/package/autoicd) — `npm install autoicd`
- [AutoICD MCP Server](https://www.npmjs.com/package/autoicd-mcp) — For Claude Desktop, Cursor, VS Code, Windsurf, and the remote endpoint at `autoicdapi.com/api/mcp`
- [Postman Collection](https://autoicdapi.com/docs) — Importable collection for the full REST surface
- [SNOMED CT & UMLS Cross-References](https://autoicdapi.com/snomed-ct-umls) — Terminology mappings
- [ICD-10-CM 2025 Code Set](https://www.cms.gov/medicare/coding-billing/icd-10-codes) — Official CMS reference

---

## License

MIT
