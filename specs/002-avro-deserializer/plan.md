# Implementation Plan: Avro Deserializer (Consumer Side)

**Branch**: `002-avro-deserializer` | **Date**: 2026-03-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-avro-deserializer/spec.md`

## Summary

Implement the consumer-side Avro deserialization pipeline: extend `ApicurioRegistryClient` with ID-based schema lookups (`get_schema_by_global_id`, `get_schema_by_content_id`), add `AvroDeserializer` (bytes-to-dict with Confluent wire format parsing), and add `DeserializationError` for consumer-side failures. Uses `fastavro.schemaless_reader` for Avro binary decoding and the Apicurio Registry v3 `/ids/` endpoints for reverse schema resolution.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: fastavro (Avro decoding), httpx (HTTP client) -- both already in runtime deps
**Storage**: N/A (in-memory schema cache only)
**Testing**: pytest, pytest-cov (100% line+branch), respx (httpx mocking)
**Target Platform**: Cross-platform Python library (PyPI package)
**Project Type**: Single Python library
**Performance Goals**: 1 HTTP call per unique schema ID regardless of message count (SC-003)
**Constraints**: No external schema-definition library in core dependencies (Principle II)
**Scale/Scope**: 1 new public class, 2 new client methods, 1 new error class, ~150 lines of new production code

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. API Compatibility First | ALIGNED | `AvroDeserializer` class name, `__call__(data, ctx)` signature, and `from_dict` hook mirror confluent-kafka conventions (SC-004) |
| II. No Schema Representation Opinion | ALIGNED | Returns plain dicts. Optional `from_dict` hook defaults to identity. No schema-definition library required. |
| III. Test-First Development | ALIGNED | TDD is MANDATORY. `/iikit-04-testify` will run before `/iikit-05-tasks`. |
| IV. Wire Format Fidelity | ALIGNED | Reads Confluent wire format (`0x00` + 4-byte ID + Avro payload). Byte-level tests verify correct parsing. |
| V. Simplicity and Minimal Footprint | ALIGNED | 0 new runtime deps. Reuses existing fastavro and httpx. No registry management. No code generation. |

**Post-design re-check**: All technical decisions (D8-D12 in research.md) verified against constitutional principles. No violations found.

## Architecture

```
                          apicurio-serdes
 ┌──────────────────────────────────────────────────────────────┐
 │                                                              │
 │   apicurio_serdes/                                           │
 │   ├── __init__.py  <-- ApicurioRegistryClient                │
 │   ├── _client.py   <-- client impl + ID-based lookups (NEW)  │
 │   ├── _errors.py   <-- + DeserializationError (NEW)          │
 │   ├── serialization.py <-- SerializationContext, MessageField │
 │   └── avro/                                                  │
 │       ├── __init__.py <-- AvroSerializer, AvroDeserializer   │
 │       ├── _serializer.py   <-- serializer impl               │
 │       └── _deserializer.py <-- deserializer impl (NEW)       │
 │                                                              │
 │   AvroSerializer ──┐                                         │
 │                     ├──> ApicurioRegistryClient               │
 │   AvroDeserializer ─┘          │                             │
 │        │                       ▼                             │
 │        ▼                  httpx.Client                       │
 │   fastavro                (HTTP session)                     │
 │   (encode/decode)                                            │
 │                                                              │
 └────────────────────────────┬─────────────────────────────────┘
                              │ HTTP
                              ▼
                   ┌───────────────────────┐
                   │ Apicurio Registry     │
                   │ v3 API                │
                   │  /groups/.../content  │
                   │  /ids/globalIds/...   │
                   │  /ids/contentIds/...  │
                   └───────────────────────┘
```

## Project Structure

### Documentation (this feature)

```text
specs/002-avro-deserializer/
  spec.md              # Feature specification
  plan.md              # This file
  research.md          # Technology decisions (D8-D12)
  data-model.md        # Entity definitions and relationships
  quickstart.md        # Usage examples and test scenarios
  contracts/
    public-api.md      # Public class/method signatures
```

### Source Code (repository root)

```text
src/
  apicurio_serdes/
    __init__.py            # Re-exports: ApicurioRegistryClient (unchanged)
    _client.py             # + get_schema_by_global_id, get_schema_by_content_id (MODIFIED)
    _errors.py             # + DeserializationError, SchemaNotFoundError.from_id (MODIFIED)
    serialization.py       # SerializationContext, MessageField (unchanged)
    py.typed               # PEP 561 marker (unchanged)
    avro/
      __init__.py          # + re-export AvroDeserializer (MODIFIED)
      _serializer.py       # AvroSerializer implementation (unchanged)
      _deserializer.py     # AvroDeserializer implementation (NEW)

tests/
  conftest.py              # + deserializer fixtures, ID-based mock routes (MODIFIED)
  test_client.py           # + ID-based lookup tests (MODIFIED)
  test_deserializer.py     # AvroDeserializer tests (NEW)
  test_wire_format.py      # + deserialization wire format tests (MODIFIED)
```

**Structure Decision**: Extends the existing `src/` layout from feature 001. New production code is a single file (`_deserializer.py`). Tests extend existing files where the system under test is shared (client, wire format) and add one new file for deserializer-specific tests.

## Key Technical Decisions

All decisions are documented in [research.md](research.md) with rationale, alternatives rejected, and constitution checks.

| ID | Decision | Choice | Research Ref |
|----|----------|--------|-------------|
| D8 | ID-based schema endpoint | `/ids/globalIds/{id}`, `/ids/contentIds/{id}` | research.md#D8 |
| D9 | Avro deserialization | `fastavro.schemaless_reader` | research.md#D9 |
| D10 | Error class design | `DeserializationError` + `SchemaNotFoundError.from_id` | research.md#D10 |
| D11 | Deserializer use_id default | `"contentId"` (per FR-006) | research.md#D11 |
| D12 | ID-based caching | Separate `_id_cache` dict, shared lock | research.md#D12 |

## Implementation Strategy

### Phase 1: DeserializationError + SchemaNotFoundError Extension

- Add `DeserializationError` to `_errors.py` (message + optional cause)
- Add `SchemaNotFoundError.from_id` classmethod for ID-based 404s
- Tests first: error construction, message format, cause chaining, `from_id` attributes

### Phase 2: ApicurioRegistryClient ID-Based Lookups

- Add `_id_cache: dict[tuple[str, int], dict[str, Any]]` to client
- Implement `get_schema_by_global_id(global_id: int) -> dict[str, Any]`
  - Endpoint: `GET /ids/globalIds/{globalId}`
  - Response: raw bytes parsed as JSON (`json.loads(response.content)`)
  - Cache key: `("globalId", global_id)`
- Implement `get_schema_by_content_id(content_id: int) -> dict[str, Any]`
  - Endpoint: `GET /ids/contentIds/{contentId}`
  - Cache key: `("contentId", content_id)`
- Both methods: double-checked locking with existing `_lock`, `SchemaNotFoundError.from_id` on 404, `RegistryConnectionError` on network failure
- Tests first: cache hit/miss, thread safety, 404 handling, network error handling

### Phase 3: AvroDeserializer

- Implement `AvroDeserializer.__init__` (registry_client, from_dict, use_id)
- Implement `AvroDeserializer.__call__` (data, ctx):
  1. Validate length >= 5 (FR-004) -> `DeserializationError`
  2. Validate `data[0] == 0x00` (FR-003) -> `DeserializationError`
  3. Extract ID: `struct.unpack(">I", data[1:5])[0]`
  4. Resolve schema by ID via client method (selected by `use_id`)
  5. Parse schema with `fastavro.parse_schema()` (cache in `_parsed_cache`)
  6. Decode: `fastavro.schemaless_reader(BytesIO(data[5:]), parsed_schema)` (FR-011 on failure)
  7. Apply `from_dict` if configured (FR-008, FR-009 on failure)
  8. Return result
- Re-export from `apicurio_serdes.avro.__init__`
- Tests first: valid decode, bad magic, short input, unknown ID, corrupt payload, from_dict hook, from_dict error

### Phase 4: Integration + Polish

- Round-trip test: serialize with `AvroSerializer`, deserialize with `AvroDeserializer`, assert equality (SC-002, SC-005)
- Wire format byte-level verification (both globalId and contentId modes)
- Cache performance test: 1000 messages same schema ID = 1 HTTP call (SC-003)
- Thread safety test: concurrent deserialization (NFR-001)
- Type annotation completeness (mypy strict)
- Coverage gate verification (100% line + branch)
- API comparison with confluent-kafka conventions (SC-004)

## Dependencies

### Runtime (no changes)

| Package | Version | Justification |
|---------|---------|---------------|
| fastavro | >=1.9.0 | Avro binary decoding via `schemaless_reader`. Already a dependency. |
| httpx | >=0.27.0 | HTTP client for registry ID-based endpoints. Already a dependency. |

### Development (no changes)

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >=8.0.0 | Test runner |
| pytest-cov | >=5.0.0 | Coverage measurement (line + branch) |
| respx | >=0.21.0 | httpx request mocking for ID-based endpoints |
| mypy | >=1.10.0 | Static type checking |
| ruff | >=0.5.0 | Linting and formatting |
| pytest-bdd | >=8.0.0 | BDD step definitions for .feature files |

## Requirements Traceability

| Requirement | Phase | Plan Section |
|-------------|-------|--------------|
| FR-001 | Phase 3: AvroDeserializer | Architecture, Implementation Strategy Phase 3 |
| FR-002 | Phase 3: AvroDeserializer | Architecture, Implementation Strategy Phase 3 |
| FR-003 | Phase 3: AvroDeserializer | Implementation Strategy Phase 3 (step 2) |
| FR-004 | Phase 3: AvroDeserializer | Implementation Strategy Phase 3 (step 1) |
| FR-005 | Phase 3: AvroDeserializer | Implementation Strategy Phase 3 (step 4) |
| FR-006 | Phase 3: AvroDeserializer | Key Technical Decisions D11, Implementation Strategy Phase 3 |
| FR-007 | Phase 2: Client ID-Based Lookups | Implementation Strategy Phase 2 |
| FR-008 | Phase 3: AvroDeserializer | Implementation Strategy Phase 3 (step 7) |
| FR-009 | Phase 1: DeserializationError + Phase 3 | Implementation Strategy Phase 1, Phase 3 (step 7) |
| FR-010 | Phase 1: SchemaNotFoundError.from_id + Phase 2 | Implementation Strategy Phase 1, Phase 2 |
| FR-011 | Phase 1: DeserializationError + Phase 3 | Implementation Strategy Phase 1, Phase 3 (step 6) |
| FR-012 | Phase 2: Client ID-Based Lookups | Implementation Strategy Phase 2 |
| NFR-001 | Phase 2: Client ID-Based Lookups + Phase 4 | Implementation Strategy Phase 2, Phase 4 |
| SC-001 | Phase 4: Integration + Polish | Summary, Implementation Strategy Phase 4 |
| SC-002 | Phase 4: Integration + Polish | Implementation Strategy Phase 4 |
| SC-003 | Phase 2: Client ID-Based Lookups + Phase 4 | Technical Context: Performance Goals, Phase 4 |
| SC-004 | Phase 4: Integration + Polish | Constitution Check table |
| SC-005 | Phase 4: Integration + Polish | Implementation Strategy Phase 4 |

## Complexity Tracking

No constitutional violations to justify. All decisions are aligned. Zero new runtime dependencies.
