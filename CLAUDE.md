# AutoICD Python SDK

Public SDK for **AutoICD API** (autoicdapi.com). Published as `autoicd` on PyPI.
GitHub: `github.com/fcggamou/autoicd-python`

## Quick Reference

```bash
pip install -e ".[dev]"  # Install in dev mode with test deps
pytest                   # Run tests
ruff check src/ tests/   # Lint
ruff format src/ tests/  # Format
```

## Architecture

```
src/autoicd/
├── __init__.py   — Public exports (re-exports client, types, errors)
├── client.py     — AutoICD class + ICD10/ICD11 sub-resources + HTTP internals
├── types.py      — All request/response dataclasses
└── errors.py     — AutoICDError hierarchy (401, 404, 429)
tests/
└── test_client.py — Unit tests with mocked httpx transport
```

- **Single dependency** — `httpx` for HTTP (timeout, headers, mock transport for tests)
- Uses `src/` layout with hatchling build backend
- Target: Python 3.10+
- All types are dataclasses — no Pydantic dependency

## API Surface

```python
client = AutoICD(api_key="sk_...")

client.code(text, options?)        # POST /api/v1/code — clinical text → ICD-10 codes
client.anonymize(text)             # POST /api/v1/anonymize — PHI de-identification
client.icd10.search(query, opts?)  # GET  /api/v1/icd10/codes/search — search ICD-10 codes
client.icd10.get(code)             # GET  /api/v1/icd10/codes/:code — code details
client.icd11.search(query, opts?)  # GET  /api/v1/icd11/codes/search — search ICD-11 codes
client.icd11.get(code)             # GET  /api/v1/icd11/codes/:code — code details
client.last_rate_limit             # Rate limit info from last response
```

## Conventions

- All names use **snake_case** (Python convention matches API response format)
- Options are passed as dataclass instances (e.g., `CodeOptions(top_k=3)`)
- `None` option values are stripped from request bodies before sending
- API responses use **snake_case** — dataclasses mirror the raw API shapes, no transformation
- Error classes: `AutoICDError` (base), `AuthenticationError` (401), `NotFoundError` (404), `RateLimitError` (429)
- Rate limit headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- API keys start with `sk_`
- Base URL defaults to `https://autoicdapi.com`, no trailing slash
- All HTTP goes through the private `_request()` method — single place for auth, timeout, error handling, rate limit parsing
- Client supports context manager (`with AutoICD(...) as client:`)

## This Is a Marketing Asset

The README, pyproject.toml description, and keywords are **SEO-optimized** to drive traffic to autoicdapi.com. When editing:

- Keep the README rich with examples, use cases, and links back to autoicdapi.com
- Maintain keyword density in pyproject.toml (icd-10, medical-coding, clinical-nlp, etc.)
- Use real-looking clinical examples in code samples (they appear in search results)
- Brand name is **AutoICD API** — always capitalize correctly

## Git Identity

This is a **public repo**. All commits MUST be authored by the AutoICD brand — never use personal or work identities.

Before committing, always use repo-local git config:
```bash
git -C /Users/fede/repos/autoicd/sdk-py commit --author="AutoICD <info@autoicdapi.com>"
```

If creating commits via the CLI, always pass `--author="AutoICD <info@autoicdapi.com>"`.

## Sync with API

The SDK calls the Next.js API routes at `api/src/app/api/v1/`. Any changes to API request/response shapes must be reflected here:

- Route changes → update paths in `client.py`
- Response shape changes → update dataclasses in `types.py`
- New endpoints → add method to `AutoICD` or `Codes` class, export types from `__init__.py`
- Test against live API or local dev server (port 3000) with `base_url="http://localhost:3000"`
