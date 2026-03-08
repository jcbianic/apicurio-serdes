# Implementation Plan: Async Registry Client

**Branch**: `003-async-registry-client` | **Date**: 2026-03-07 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-async-registry-client/spec.md`

## Summary

Add `AsyncApicurioRegistryClient` — an async-native variant of `ApicurioRegistryClient` that uses `httpx.AsyncClient` for non-blocking registry communication. Exposes an identical interface to the sync client (same constructor parameters, same `get_schema` method) with `await` as the only calling-convention difference. Adds async context manager support (`async with`) and an explicit `aclose()` method. No new runtime dependencies: `httpx` already provides `AsyncClient`. One new dev dependency: `pytest-asyncio` for async test functions.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: httpx (AsyncClient — already a runtime dependency)
**Storage**: N/A (in-memory schema cache only)
**Testing**: pytest, pytest-cov (100% line+branch), respx (async httpx mocking), pytest-asyncio
**Target Platform**: Cross-platform Python library (PyPI package)
**Project Type**: Single Python library
**Performance Goals**: 1 HTTP call per unique artifact_id regardless of coroutine count (SC-003)
**Constraints**: No new runtime dependencies (httpx.AsyncClient ships with httpx). No ID-based methods in MVP (spec scope). (Principle V)
**Scale/Scope**: 1 new public class (~80 lines of production code), 1 new test file

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. API Compatibility First | ALIGNED | Constructor signature and `get_schema` method mirror the sync client exactly (SC-004). Only `await` and class name differ. |
| II. No Schema Representation Opinion | ALIGNED | Accepts plain `artifact_id` strings. Returns `CachedSchema` (same value object as sync client). No schema library coupling. |
| III. Test-First Development | ALIGNED | TDD is MANDATORY. `/iikit-04-testify` will run before `/iikit-05-tasks`. |
| IV. Wire Format Fidelity | N/A | This feature adds a client, not a serializer. Wire format is unchanged. |
| V. Simplicity and Minimal Footprint | ALIGNED | Zero new runtime deps. `httpx.AsyncClient` is already shipped with the `httpx` runtime dependency. |

## Architecture

```
                        apicurio-serdes
 ┌────────────────────────────────────────────────────────┐
 │                                                        │
 │   apicurio_serdes/                                     │
 │   ├── __init__.py  ←─ ApicurioRegistryClient           │
 │   │                   AsyncApicurioRegistryClient      │
 │   ├── _client.py   ←─ sync client + CachedSchema       │
 │   ├── _async_client.py ←─ async client implementation  │
 │   ├── _errors.py   ←─ SchemaNotFoundError, etc.        │
 │   ├── serialization.py ←─ SerializationContext          │
 │   └── avro/                                            │
 │       └── _serializer.py ←─ AvroSerializer             │
 │                                                        │
 │  AvroSerializer ──calls──→ ApicurioRegistryClient      │
 │                                                        │
 │  AsyncApicurioRegistryClient                           │
 │      ├── uses──→ httpx.AsyncClient (async HTTP)        │
 │      └── shares──→ CachedSchema (from _client.py)      │
 │                                                        │
 │  ApicurioRegistryClient                                │
 │      └── uses──→ httpx.Client (sync HTTP)              │
 │                                                        │
 └──────────────────────┬─────────────────────────────────┘
                        │ HTTP / HTTPS
                        ▼
             ┌──────────────────────┐
             │ Apicurio             │
             │ Registry v3 API      │
             └──────────────────────┘
```

## Project Structure

### Documentation (this feature)

```text
specs/003-async-registry-client/
  spec.md              # Feature specification
  plan.md              # This file
  research.md          # Technology decisions and findings
  data-model.md        # Entity definitions and relationships
  quickstart.md        # Usage examples and test scenarios
  contracts/
    public-api.md      # Public class/method signatures
```

### Source Code (repository root)

```text
src/
  apicurio_serdes/
    __init__.py            # Re-exports: ApicurioRegistryClient, AsyncApicurioRegistryClient
    _client.py             # ApicurioRegistryClient + CachedSchema (unchanged)
    _async_client.py       # AsyncApicurioRegistryClient (NEW)
    _errors.py             # SchemaNotFoundError, RegistryConnectionError (unchanged)
    serialization.py       # SerializationContext, MessageField (unchanged)
    py.typed               # PEP 561 marker
    avro/
      __init__.py          # Re-exports: AvroSerializer
      _serializer.py       # AvroSerializer implementation

tests/
  conftest.py              # Shared fixtures
  test_async_client.py     # AsyncApicurioRegistryClient tests (NEW)
  test_client.py           # ApicurioRegistryClient tests (existing)
  ...

pyproject.toml             # Add pytest-asyncio to dev dependencies
```

**Structure Decision**: New file `_async_client.py` alongside `_client.py`. The `CachedSchema` dataclass remains in `_client.py` and is imported by `_async_client.py` to avoid duplication (FR-003). A single new test file `test_async_client.py` covers all async client behaviour.

## Key Technical Decisions

All decisions are documented in [research.md](research.md) with rationale, alternatives rejected, and constitution checks.

Decisions D1–D12 are inherited from features 001 and 002. This feature adds D13–D17.

| ID | Decision | Choice | Research Ref |
|----|----------|--------|-------------|
| D13 | Async HTTP transport | httpx.AsyncClient | research.md#D13 |
| D14 | Async cache safety | asyncio.Lock + double-check | research.md#D14 |
| D15 | Async test support | pytest-asyncio | research.md#D15 |
| D16 | File placement | _async_client.py | research.md#D16 |
| D17 | ID-based methods | Excluded from async MVP | research.md#D17 |

## Implementation Strategy

### Phase 1: Dev Dependency Update

- Add `pytest-asyncio>=0.23.0` to `[dependency-groups] dev` in `pyproject.toml`
- Run `uv lock --upgrade-package pytest-asyncio` to update lockfile

### Phase 2: AsyncApicurioRegistryClient

- Create `src/apicurio_serdes/_async_client.py`
- Import `CachedSchema` from `._client` (FR-003: shared value object)
- Import errors from `._errors`
- Implement `AsyncApicurioRegistryClient` with:
  - `__init__(url, group_id)` — same validation as sync client (FR-008)
  - `async get_schema(artifact_id)` — async fetch + cache (FR-001, FR-002, FR-004)
  - `async __aenter__` / `async __aexit__` — context manager (FR-009)
  - `async aclose()` — explicit close (FR-010)
  - `asyncio.Lock` for concurrency safety (NFR-001)

### Phase 3: Package Export

- Update `src/apicurio_serdes/__init__.py` to re-export `AsyncApicurioRegistryClient`
- Update `__all__` to include it (FR-011)

### Phase 4: Tests

- `tests/test_async_client.py` covering all FR/NFR/SC scenarios
- `respx` async mock for `httpx.AsyncClient`

### Phase 5: Polish

- mypy strict compliance
- 100% line + branch coverage gate
- Docstrings on all public symbols

## Dependencies

### Runtime

| Package | Version | Justification |
|---------|---------|---------------|
| httpx | >=0.27.0 | `httpx.AsyncClient` is part of httpx. No version change needed. |

### Development (additions)

| Package | Version | Purpose |
|---------|---------|---------|
| pytest-asyncio | >=0.23.0 | Async test function support (`@pytest.mark.asyncio`). No stdlib alternative. |

## Requirements Traceability

| Requirement | Phase | Plan Section |
|-------------|-------|--------------|
| FR-001 | Phase 2 | Implementation Strategy §Phase 2 |
| FR-002 | Phase 2 | Implementation Strategy §Phase 2 |
| FR-003 | Phase 2 | Project Structure (CachedSchema import) |
| FR-004 | Phase 2 | Implementation Strategy §Phase 2 |
| FR-005 | Phase 2 | Implementation Strategy §Phase 2 |
| FR-006 | Phase 2 | Implementation Strategy §Phase 2 |
| FR-007 | Phase 2 | Implementation Strategy §Phase 2 |
| FR-008 | Phase 2 | Implementation Strategy §Phase 2 |
| FR-009 | Phase 2 | Implementation Strategy §Phase 2 |
| FR-010 | Phase 2 | Implementation Strategy §Phase 2 |
| FR-011 | Phase 3 | Implementation Strategy §Phase 3 |
| NFR-001 | Phase 2 | Key Technical Decisions D14 |
| SC-001 | Phase 4 | Implementation Strategy §Phase 4 |
| SC-002 | Phase 3 | Project Structure (shared CachedSchema) |
| SC-003 | Phase 2 | Technical Context: Performance Goals |
| SC-004 | Phase 2 | Constitution Check table |

## Complexity Tracking

No constitutional violations to justify. All decisions are aligned.
