# Implementation Plan: Avro Serializer (Producer Side)

**Branch**: `001-avro-serializer` | **Date**: 2026-03-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-avro-serializer/spec.md`

## Summary

Implement the producer-side Avro serialization pipeline: `ApicurioRegistryClient` (HTTP client with schema caching), `AvroSerializer` (dict-to-bytes with Confluent wire framing), `SerializationContext` and `MessageField` (Kafka metadata). Uses `fastavro` for Avro binary encoding and `httpx` for HTTP communication with the Apicurio Registry v3 native API.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: fastavro (Avro encoding), httpx (HTTP client)
**Storage**: N/A (in-memory schema cache only)
**Testing**: pytest, pytest-cov (100% line+branch), respx (httpx mocking)
**Target Platform**: Cross-platform Python library (PyPI package)
**Project Type**: Single Python library
**Performance Goals**: 1 HTTP call per unique artifact_id regardless of message count (SC-003)
**Constraints**: No external schema-definition library in core dependencies (Principle II)
**Scale/Scope**: 4 public classes, ~300 lines of production code

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. API Compatibility First | ALIGNED | Import paths and class names mirror confluent-kafka conventions (SC-004) |
| II. No Schema Representation Opinion | ALIGNED | Accepts plain dicts and raw schema strings. fastavro is an encoder, not a schema definition library. Optional `to_dict` hook defaults to identity. |
| III. Test-First Development | ALIGNED | TDD is MANDATORY. `/iikit-04-testify` will run before `/iikit-05-tasks`. |
| IV. Wire Format Fidelity | ALIGNED | Confluent wire format (`0x00` + 4-byte globalId + Avro payload) verified with byte-level tests. |
| V. Simplicity and Minimal Footprint | ALIGNED | 2 runtime deps (fastavro, httpx), both justified. No registry management. No code generation. |

## Architecture

```
                        apicurio-serdes
 ┌─────────────────────────────────────────────────┐
 │                                                  │
 │   apicurio_serdes/                               │
 │   ├── __init__.py  ←─ ApicurioRegistryClient     │
 │   ├── _client.py   ←─ client implementation      │
 │   ├── _errors.py   ←─ SchemaNotFoundError        │
 │   ├── serialization.py ←─ SerializationContext,   │
 │   │                       MessageField            │
 │   └── avro/                                       │
 │       ├── __init__.py ←─ AvroSerializer           │
 │       └── _serializer.py ←─ serializer impl       │
 │                                                   │
 │   AvroSerializer ──calls──→ ApicurioRegistryClient│
 │        │                         │                │
 │        ▼                         ▼                │
 │   fastavro                  httpx.Client          │
 │   (Avro encode)             (HTTP session)        │
 │                                                   │
 └─────────────────────────────┬───────────────────-─┘
                               │ HTTP
                               ▼
                    ┌──────────────────┐
                    │ Apicurio         │
                    │ Registry v3 API  │
                    └──────────────────┘
```

## Project Structure

### Documentation (this feature)

```text
specs/001-avro-serializer/
  spec.md              # Feature specification
  plan.md              # This file
  research.md          # Technology decisions and findings
  data-model.md        # Entity definitions and relationships
  quickstart.md        # Usage examples and test scenarios
  contracts/           # API contracts
    public-api.md      # Public class/method signatures
```

### Source Code (repository root)

```text
src/
  apicurio_serdes/
    __init__.py            # Re-exports: ApicurioRegistryClient
    _client.py             # ApicurioRegistryClient implementation
    _errors.py             # SchemaNotFoundError
    serialization.py       # SerializationContext, MessageField
    py.typed               # PEP 561 marker
    avro/
      __init__.py          # Re-exports: AvroSerializer
      _serializer.py       # AvroSerializer implementation

tests/
  conftest.py              # Shared fixtures (mock registry, sample schemas)
  test_client.py           # ApicurioRegistryClient tests
  test_serializer.py       # AvroSerializer tests
  test_serialization.py    # SerializationContext, MessageField tests
  test_wire_format.py      # Byte-level wire format verification

pyproject.toml             # Build config, dependencies, tool settings
```

**Structure Decision**: Single Python library using `src/` layout (PEP 517 recommended). The `src/` layout prevents accidental imports from the project root during testing. Tests are flat (no subdirectories) since the feature scope is small enough that subdivision adds overhead without value.

## Key Technical Decisions

All decisions are documented in [research.md](research.md) with rationale, alternatives rejected, and constitution checks.

| ID | Decision | Choice | Research Ref |
|----|----------|--------|-------------|
| D1 | Avro library | fastavro | research.md#D1 |
| D2 | HTTP client | httpx | research.md#D2 |
| D3 | Python version | 3.10+ | research.md#D3 |
| D4 | Build tooling | uv + hatchling + ruff + mypy | research.md#D4 |
| D5 | Testing | pytest + pytest-cov + respx | research.md#D5 |
| D6 | Wire format ID | globalId (Apicurio 3.x default) | research.md#D6 |
| D7 | Registry endpoint | GET .../versions/latest/content | research.md#D7 |

## Implementation Strategy

### Phase 1: Project Scaffolding
- `pyproject.toml` with build config, dependencies, tool settings
- `src/` layout with `__init__.py` files
- `py.typed` marker for PEP 561
- `conftest.py` with shared test fixtures

### Phase 2: SerializationContext + MessageField
- Simplest entities, no external dependencies
- `MessageField` enum (KEY, VALUE)
- `SerializationContext` dataclass (topic, field)

### Phase 3: ApicurioRegistryClient
- HTTP communication with registry via httpx
- Schema caching by `(group_id, artifact_id)`
- `SchemaNotFoundError` for 404 responses
- Response header parsing for `X-Registry-GlobalId`

### Phase 4: AvroSerializer
- Confluent wire format encoding (`0x00` + 4-byte globalId + Avro payload)
- Schema fetch delegation to client (lazy, on first call)
- `to_dict` hook integration
- Byte-level wire format tests

### Phase 5: Integration + Polish
- End-to-end test with mocked registry
- Wire format byte-level verification against known reference messages
- Type annotation completeness (mypy strict)
- Coverage gate verification (100% line + branch)

## Dependencies

### Runtime

| Package | Version | Justification |
|---------|---------|---------------|
| fastavro | >=1.9.0 | Avro binary encoding/decoding. Required — no stdlib alternative. |
| httpx | >=0.27.0 | HTTP client for registry communication. Provides sync+async in one package. |

### Development

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >=8.0.0 | Test runner |
| pytest-cov | >=5.0.0 | Coverage measurement (line + branch) |
| respx | >=0.21.0 | httpx request mocking |
| mypy | >=1.10.0 | Static type checking |
| ruff | >=0.5.0 | Linting and formatting |
| pytest-bdd | >=7.0.0 | BDD step definitions for .feature files |

## Requirements Traceability

| Requirement | Phase | Plan Section |
|-------------|-------|--------------|
| FR-001 | Phase 3: ApicurioRegistryClient | Architecture, Implementation Strategy §Phase 3 |
| FR-002 | Phase 4: AvroSerializer | Architecture, Implementation Strategy §Phase 4 |
| FR-003 | Phase 4: AvroSerializer | Architecture, Implementation Strategy §Phase 4 |
| FR-004 | Phase 2: SerializationContext + MessageField | Architecture, Implementation Strategy §Phase 2 |
| FR-005 | Phase 4: AvroSerializer | Architecture, Implementation Strategy §Phase 4 |
| FR-006 | Phase 3: ApicurioRegistryClient | Architecture, Implementation Strategy §Phase 3 |
| FR-007 | Phase 4: AvroSerializer | Architecture, Implementation Strategy §Phase 4 |
| FR-008 | Phase 3: ApicurioRegistryClient | Architecture, Implementation Strategy §Phase 3 |
| FR-009 | Phase 3: ApicurioRegistryClient | Architecture, Implementation Strategy §Phase 3 |
| FR-010 | Phase 4: AvroSerializer | Key Technical Decisions D6, Implementation Strategy §Phase 4 |
| FR-011 | Phase 3: ApicurioRegistryClient | Architecture, Implementation Strategy §Phase 3 |
| FR-012 | Phase 4: AvroSerializer | Implementation Strategy §Phase 4 |
| FR-013 | Phase 4: AvroSerializer | Implementation Strategy §Phase 4 |
| NFR-001 | Phase 3: ApicurioRegistryClient | Implementation Strategy §Phase 3 |
| SC-001 | Phase 5: Integration + Polish | Summary, Implementation Strategy §Phase 5 |
| SC-002 | Phase 5: Integration + Polish | Implementation Strategy §Phase 5 |
| SC-003 | Phase 3: ApicurioRegistryClient | Technical Context: Performance Goals |
| SC-004 | Phase 5: Integration + Polish | Constitution Check table |

## Complexity Tracking

No constitutional violations to justify. All decisions are aligned.
