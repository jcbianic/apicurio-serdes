# Research: Avro Serializer (Producer Side)

**Feature**: 001-avro-serializer | **Date**: 2026-03-06

## Decision Log

### D1: Avro Library — fastavro vs apache-avro

**Decision**: `fastavro`

**Rationale**:
- 10-100x faster than `apache-avro` for encoding/decoding (C/Cython implementation)
- More Pythonic API: `fastavro.schemaless_writer(output, schema, record)` for single-record encoding
- Actively maintained, ~2.5k GitHub stars, widely used in Kafka Python ecosystem
- Lighter dependency footprint than `apache-avro`
- Supports schemaless writing (no file container) which is exactly what we need for wire format embedding

**Alternatives rejected**:
- `apache-avro`: Reference implementation but pure Python, slower, heavier. Only advantage is "official" status, which is outweighed by performance for a serialization library.

**Constitution check**: Per Principle V (minimal footprint), fastavro is the leaner choice. Per Principle V (dependency justification): fastavro is required for Avro binary encoding — no stdlib alternative exists.

### D2: HTTP Client — httpx

**Decision**: `httpx`

**Rationale**:
- Sync and async support in one library (matches design principle 6: sync-first, async-friendly)
- Modern, well-tested, good error handling and connection pooling
- `httpx.Client` provides persistent sessions for connection reuse
- Clean API for setting base URLs and default headers
- Tessl tile available (`tessl/pypi-httpx@0.28.0`)

**Alternatives rejected**:
- `requests`: Sync only. Would require a separate async library (aiohttp/httpx) for async support, violating DRY.
- `urllib3`: Too low-level for a clean public API. Would need significant wrapper code.
- `aiohttp`: Async only. Would need sync wrappers for the primary interface.

**Constitution check**: Per Principle V (dependency justification): httpx is required for HTTP communication with the registry — no stdlib alternative provides the needed session management and async support.

### D3: Python Minimum Version — 3.10+

**Decision**: Python 3.10+

**Rationale**:
- Union type syntax `X | Y` (PEP 604) — cleaner type annotations
- Structural pattern matching (PEP 634) — useful for error handling
- Python 3.9 reached EOL October 2025
- Python 3.10 EOL October 2026 — still within support window
- Red Hat Enterprise Linux 9.x ships Python 3.11, but some enterprise users may be on 3.10

**Note**: Plan to bump minimum to 3.11+ after October 2026 when 3.10 reaches EOL.

**Alternatives rejected**:
- Python 3.9+: Already EOL. Supporting it adds maintenance burden for no meaningful user gain.
- Python 3.11+: Would exclude users on Python 3.10. Can bump later.

### D4: Build System and Tooling

**Decision**: `uv` + `hatchling` + `ruff` + `mypy`

**Rationale**:
- `uv`: Fast, modern dependency management and virtual environment tooling
- `hatchling`: Simple, standards-compliant build backend (PEP 517/518)
- `ruff`: Fast linter and formatter (replaces flake8 + black + isort)
- `mypy`: Type checker (constitution requires static type annotations on all public symbols)

### D5: Testing Framework

**Decision**: `pytest` + `pytest-cov` + `respx`

**Rationale**:
- `pytest`: Standard Python testing framework, rich plugin ecosystem
- `pytest-cov`: Coverage measurement with `--branch` flag (constitution: 100% line + branch)
- `respx`: Mock library specifically designed for httpx (cleaner than generic mocking)
- Tessl tiles available for pytest (`tessl/pypi-pytest@8.4.0`) and pytest-cov (`tessl/pypi-pytest-cov@6.2.0`)

### D6: Wire Format ID — globalId (default)

**Decision**: Use `globalId` as the 4-byte schema identifier in the Confluent wire format header.

**Rationale**:
- Apicurio 3.x Java serde defaults to `globalId` for the Confluent wire format
- `globalId` is a per-version monotonically increasing integer — unique per artifact version
- Matches the behavior users expect when migrating from confluent-kafka (which uses schema ID = a per-version integer)
- The intent document mentions defaulting to `contentId`, but the Apicurio Java serde actually defaults to `globalId`. We follow the Java serde default for compatibility (SC-002: byte-for-byte compatible with Apicurio native serializer).

**Note**: The intent doc's open question #2 (contentId vs globalId) is resolved here. Future features may add a `use_id` configuration option.

**Verification needed**: Confirm against live Apicurio 3.x serde source code that `globalId` is indeed the default for `IdOption` in the Confluent wire format handler.

### D7: Apicurio v3 API Endpoint for Schema Retrieval

**Decision**: Use `GET /groups/{groupId}/artifacts/{artifactId}/versions/latest/content`

**Rationale**:
- Returns the raw schema content (JSON string for Avro)
- Response headers include: `X-Registry-ContentId`, `X-Registry-GlobalId`, `X-Registry-ArtifactId`, `X-Registry-ArtifactType`, `X-Registry-Version`
- Returns HTTP 404 with JSON error envelope when artifact not found
- Base path: `/apis/registry/v3`

**Full URL pattern**:
```
{base_url}/groups/{group_id}/artifacts/{artifact_id}/versions/latest/content
```

**Error response (404)**:
```json
{
  "error_code": 404,
  "message": "No artifact with ID '...' in group '...' was found."
}
```

**Verification needed**: Confirm exact endpoint path and response header names against live Apicurio 3.x instance or OpenAPI spec. The path may be `/content` directly on the artifact (without `/versions/latest/`) in some 3.x builds.

## fastavro Usage Patterns

### Schemaless Writing (single record to bytes)

```python
import io
import json
import fastavro

# Parse schema from JSON string
schema_str = '{"type": "record", "name": "User", "fields": [...]}'
schema = fastavro.parse_schema(json.loads(schema_str))

# Write single record to bytes
buffer = io.BytesIO()
fastavro.schemaless_writer(buffer, schema, record)
payload = buffer.getvalue()
```

### Error Handling

- Missing required field: raises `ValueError` (e.g., `"no value and no default for name"`)
- Wrong type: raises `ValueError`
- Schema parse error: raises `fastavro.schema.SchemaParseException`

### Best Practices

- Always use `fastavro.parse_schema()` to normalize the schema before encoding — this resolves named types and handles schema references
- Use `schemaless_writer` (not `writer`) for single-record encoding without Avro container file overhead
- Parse the schema once and reuse it — aligns with our caching strategy

## Tessl Tiles

### Installed Tiles

| Technology | Tile | Type | Version | Eval |
|------------|------|------|---------|------|
| httpx | tessl/pypi-httpx | docs | 0.28.0 | N/A |
| pytest | tessl/pypi-pytest | docs | 8.4.0 | N/A |
| pytest-cov | tessl/pypi-pytest-cov | docs | 6.2.0 | N/A |

### Technologies Without Tiles

- fastavro: No tile found
- Apicurio Registry: No tile found
- respx: Not searched (httpx mock library)
