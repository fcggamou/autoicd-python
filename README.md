# AutoICD API — Python SDK

[![PyPI version](https://img.shields.io/pypi/v/autoicd.svg)](https://pypi.org/project/autoicd/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)

Official Python SDK for the [AutoICD API](https://autoicdapi.com) — clinical text to ICD-10-CM diagnosis codes, powered by AI and medical NLP.

Single dependency (`httpx`). Works in **Python 3.10+**.

> Built for EHR integrations, health-tech platforms, medical billing, clinical decision support, and revenue cycle management.

---

## Why AutoICD API

| | |
|---|---|
| **AI-Powered ICD-10 Coding** | Clinical NLP extracts diagnoses from free-text notes and maps them to ICD-10-CM codes — no manual lookup required |
| **74,000+ ICD-10-CM Codes** | Full 2025 code set enriched with SNOMED CT synonyms for comprehensive matching |
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
results = client.codes.search("diabetes mellitus")
# results.codes → [CodeDetail(code="E11.9", short_description="...", ...), ...]

from autoicd import SearchOptions
results = client.codes.search("heart failure", options=SearchOptions(limit=5))
```

### ICD-10 Code Details

Get full details for any ICD-10-CM code — descriptions, billable status, synonyms, hierarchy, and chapter classification.

```python
detail = client.codes.get("E11.9")
print(detail.code)              # "E11.9"
print(detail.long_description)  # "Type 2 diabetes mellitus without complications"
print(detail.is_billable)       # True
print(detail.synonyms["snomed"])  # ["Diabetes mellitus type 2", ...]
print(detail.chapter.title)       # "Endocrine, Nutritional and Metabolic Diseases"
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
| [Hypertension](https://autoicdapi.com/icd10/condition/hypertension) | [I10](https://autoicdapi.com/icd10/I10) | Essential (primary) hypertension |
| [Type 2 Diabetes](https://autoicdapi.com/icd10/condition/diabetes) | [E11.9](https://autoicdapi.com/icd10/E11.9) | Type 2 diabetes mellitus without complications |
| [Depression](https://autoicdapi.com/icd10/condition/depression) | [F32.9](https://autoicdapi.com/icd10/F32.9) | Major depressive disorder, single episode, unspecified |
| [Anxiety](https://autoicdapi.com/icd10/condition/anxiety) | [F41.1](https://autoicdapi.com/icd10/F41.1) | Generalized anxiety disorder |
| [Low Back Pain](https://autoicdapi.com/icd10/condition/back-pain) | [M54.5](https://autoicdapi.com/icd10/M54.5) | Low back pain |
| [COPD](https://autoicdapi.com/icd10/condition/copd) | [J44.9](https://autoicdapi.com/icd10/J44.9) | Chronic obstructive pulmonary disease, unspecified |
| [Heart Failure](https://autoicdapi.com/icd10/condition/heart-failure) | [I50.9](https://autoicdapi.com/icd10/I50.9) | Heart failure, unspecified |
| [UTI](https://autoicdapi.com/icd10/condition/urinary-tract-infection) | [N39.0](https://autoicdapi.com/icd10/N39.0) | Urinary tract infection, site not specified |
| [Pneumonia](https://autoicdapi.com/icd10/condition/pneumonia) | [J18.9](https://autoicdapi.com/icd10/J18.9) | Pneumonia, unspecified organism |
| [Atrial Fibrillation](https://autoicdapi.com/icd10/condition/atrial-fibrillation) | [I48.91](https://autoicdapi.com/icd10/I48.91) | Unspecified atrial fibrillation |
| [Obesity](https://autoicdapi.com/icd10/condition/obesity) | [E66.01](https://autoicdapi.com/icd10/E66.01) | Morbid (severe) obesity due to excess calories |
| [GERD](https://autoicdapi.com/icd10/condition/gerd) | [K21.9](https://autoicdapi.com/icd10/K21.9) | Gastro-esophageal reflux disease without esophagitis |
| [Hypothyroidism](https://autoicdapi.com/icd10/condition/hypothyroidism) | [E03.9](https://autoicdapi.com/icd10/E03.9) | Hypothyroidism, unspecified |
| [CKD](https://autoicdapi.com/icd10/condition/chronic-kidney-disease) | [N18.9](https://autoicdapi.com/icd10/N18.9) | Chronic kidney disease, unspecified |

Browse all 74,000+ codes in the [ICD-10-CM Code Directory](https://autoicdapi.com/icd10) or find codes by [condition](https://autoicdapi.com/icd10/condition).

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
| `client.code(text, options?)` | Code clinical text to ICD-10-CM diagnoses |
| `client.anonymize(text)` | De-identify PHI/PII in clinical text |
| `client.codes.search(query, options?)` | Search ICD-10-CM codes by description |
| `client.codes.get(code)` | Get details for an ICD-10-CM code |

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
- [ICD-10-CM Code Directory](https://autoicdapi.com/icd10) — Browse all 74,000+ diagnosis codes
- [ICD-10 Codes by Condition](https://autoicdapi.com/icd10/condition) — Find codes for common conditions
- [TypeScript SDK](https://www.npmjs.com/package/autoicd) — `npm install autoicd`
- [MCP Server](https://www.npmjs.com/package/autoicd-mcp) — For Claude Desktop, Cursor, VS Code
- [SNOMED CT & UMLS Cross-References](https://autoicdapi.com/snomed-ct-umls) — Terminology mappings
- [ICD-10-CM 2025 Code Set](https://www.cms.gov/medicare/coding-billing/icd-10-codes) — Official CMS reference

---

## License

MIT
