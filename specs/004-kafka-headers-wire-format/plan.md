# Implementation Plan: WireFormat.KAFKA_HEADERS Support

**Branch**: `004-kafka-headers-wire-format` | **Date**: 2026-03-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-kafka-headers-wire-format/spec.md`

## Summary

Add `WireFormat.KAFKA_HEADERS` mode to the `AvroSerializer`, allowing users to produce Avro messages where the schema identifier is carried in Kafka message headers rather than embedded in the message bytes. Introduces a `WireFormat` enum (in `serialization.py`) and a `SerializedMessage` dataclass as the return type of a new `serialize()` method. No new runtime dependencies. The CONFLUENT_PAYLOAD path is unchanged.

FR-010 is resolved: **Option C** — `AvroSerializer.serialize()` returns `SerializedMessage(payload: bytes, headers: dict[str, bytes])` for both wire format modes. `AvroSerializer.__call__` remains backward-compatible (returns `bytes` only, headers discarded when KAFKA_HEADERS mode is invoked through `__call__`).

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: fastavro (Avro encoding), httpx (HTTP client) — unchanged; no new runtime deps
**Storage**: N/A (in-memory schema cache only — unchanged)
**Testing**: pytest, pytest-bdd, pytest-cov (100% line+branch), respx (httpx mocking)
**Target Platform**: Cross-platform Python library (PyPI package)
**Project Type**: Single Python library — additive change to existing src/ layout
**Performance Goals**: 1 HTTP call per unique artifact_id regardless of message count, wire format mode, or use_id setting (SC-005, NFR-001)
**Constraints**: No new runtime dependencies. No external schema-definition library (Principle II). Header value encoding must be byte-level compatible with Apicurio Java KAFKA_HEADERS serde (FR-007, SC-002).
**Scale/Scope**: ~80 lines of new/modified production code; 4 new public symbols (WireFormat, SerializedMessage, AvroSerializer.serialize, AvroSerializer updated constructor)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. API Compatibility First | ALIGNED | `WireFormat` enum mirrors the naming pattern used in confluent-kafka's `WireFormat`. `__call__` return type is unchanged for existing callers. New `serialize()` method is additive. |
| II. No Schema Representation Opinion | ALIGNED | No new dependencies. `WireFormat` and `SerializedMessage` are stdlib-based (`enum`, `dataclasses`). `struct.pack(">q", ...)` for header encoding is stdlib. |
| III. Test-First Development | ALIGNED — MANDATORY | `/iikit-04-testify` runs before `/iikit-05-tasks`. No production code without preceding failing test. |
| IV. Wire Format Fidelity | ALIGNED | Header name constants and 8-byte big-endian encoding are documented in research.md and verified by byte-level tests. SC-002 mandates interoperability with Apicurio Java serde. |
| V. Simplicity and Minimal Footprint | ALIGNED | No strategy pattern or new abstractions for 2 wire formats. Simple conditional inside `serialize()`. No new runtime dependencies. |

## Architecture

```
apicurio-serdes (004 addition — changes in bold)
┌──────────────────────────────────────────────────────────────┐
│                                                               │
│  apicurio_serdes/                                             │
│  ├── __init__.py  ←─ ApicurioRegistryClient, [WireFormat]    │
│  ├── _client.py   ←─ (unchanged)                             │
│  ├── _errors.py   ←─ (unchanged)                             │
│  ├── serialization.py ←─ SerializationContext, MessageField, │
│  │                        [WireFormat], [SerializedMessage]   │
│  └── avro/                                                    │
│      ├── __init__.py ←─ AvroSerializer                       │
│      └── _serializer.py ←─ [wire_format param],              │
│                              [serialize() method]             │
│                                                               │
│  AvroSerializer.serialize() ──calls──→ ApicurioRegistryClient │
│        │                                    │                 │
│        ▼                                    ▼                 │
│   fastavro                           httpx.Client             │
│   (Avro encode)                      (HTTP session)           │
│                                                               │
└───────────────────────────────────────────────────────────────┘
                               │ HTTP
                               ▼
                    ┌──────────────────┐
                    │ Apicurio         │
                    │ Registry v3 API  │
                    └──────────────────┘

[brackets] = new/modified in this feature
```

## Project Structure

### Documentation (this feature)

```text
specs/004-kafka-headers-wire-format/
  spec.md              # Feature specification
  plan.md              # This file
  research.md          # Technology decisions (header naming, encoding)
  data-model.md        # Entity definitions (WireFormat, SerializedMessage)
  quickstart.md        # Usage examples
  contracts/
    public-api.md      # Updated public class/method signatures
```

### Source Code (affected files only)

```text
src/
  apicurio_serdes/
    __init__.py            # Add WireFormat to re-exports
    serialization.py       # Add WireFormat enum, SerializedMessage dataclass
    avro/
      _serializer.py       # Add wire_format param, serialize() method

tests/
  test_serialization.py    # Extend: WireFormat enum, SerializedMessage tests
  test_serializer.py       # Extend: wire_format param, KAFKA_HEADERS behavior
  test_wire_format.py      # Extend: KAFKA_HEADERS byte-level header tests
```

## FR-010 Resolution: API Surface for Headers

**Decision**: Option C — dedicated `serialize()` method on `AvroSerializer`.

```python
@dataclass(frozen=True)
class SerializedMessage:
    payload: bytes
    headers: dict[str, bytes]

class AvroSerializer:
    def serialize(self, data: Any, ctx: SerializationContext) -> SerializedMessage: ...
    def __call__(self, data: Any, ctx: SerializationContext) -> bytes: ...  # unchanged contract
```

**Rationale for Option C over A and B:**
- Option A (return type changes based on mode): makes `__call__` return type `bytes | tuple[bytes, dict]` — breaks static typing and violates Principle I (existing callers get a surprise).
- Option B (mutable `SerializationContext`): requires removing `frozen=True`, introduces side-effect coupling between caller and serializer, and is harder to test in isolation.
- Option C: fully additive. Existing callers of `__call__` see no change. New KAFKA_HEADERS users use `serialize()` and get a typed result. Both modes supported by the same method.

**Backward-compatibility note**: `__call__` delegates to `serialize()` internally and returns `result.payload`. For CONFLUENT_PAYLOAD, `payload` is the framed bytes — identical to current behavior. For KAFKA_HEADERS callers using `__call__`, the headers are silently discarded; this is documented. The recommended entry point for KAFKA_HEADERS is `serialize()`.

## Key Technical Decisions

All decisions are documented in [research.md](research.md).

| ID | Decision | Choice | Research Ref |
|----|----------|--------|-------------|
| D1 | FR-010: API surface for headers | Option C: `serialize()` returning `SerializedMessage` | research.md#D1 |
| D2 | KAFKA_HEADERS header names | Apicurio native: `apicurio.registry.{key.}globalId/contentId` | research.md#D2 |
| D3 | Header value byte encoding | 8-byte big-endian signed long (`struct.pack(">q", id)`) | research.md#D3 |
| D4 | Architecture pattern | Simple conditional in `serialize()` — no strategy pattern | research.md#D4 |
| D5 | WireFormat placement | `serialization.py` alongside `MessageField` and `SerializationContext` | research.md#D5 |
| D6 | `__init__.py` re-export | `WireFormat` re-exported from top-level (FR-002) | research.md#D6 |

## Implementation Strategy

### Phase 1: WireFormat enum + SerializedMessage dataclass

- Add `WireFormat(enum.Enum)` with `CONFLUENT_PAYLOAD` and `KAFKA_HEADERS` to `serialization.py`
- Add `SerializedMessage(payload: bytes, headers: dict[str, bytes])` frozen dataclass to `serialization.py`
- Re-export `WireFormat` from `apicurio_serdes/__init__.py`
- Tests: import, enum members, type annotations, top-level re-export

### Phase 2: `AvroSerializer.serialize()` — CONFLUENT_PAYLOAD path

- Add `wire_format: WireFormat = WireFormat.CONFLUENT_PAYLOAD` parameter to `__init__`
- Add `serialize()` method — for CONFLUENT_PAYLOAD returns `SerializedMessage(payload=framed_bytes, headers={})`
- Refactor `__call__` to delegate to `serialize()` and return `.payload`
- Tests: CONFLUENT_PAYLOAD `serialize()` output matches pre-existing `__call__` output byte-for-byte; `headers` is empty dict

### Phase 3: `AvroSerializer.serialize()` — KAFKA_HEADERS path

- Implement KAFKA_HEADERS branch in `serialize()`:
  - Encode raw Avro payload (no framing)
  - Compute header name from `MessageField` × `use_id` (4 combinations, see research.md#D2)
  - Encode schema ID as `struct.pack(">q", schema_id)` (8 bytes)
  - Return `SerializedMessage(payload=raw_avro, headers={header_name: header_value})`
- Tests:
  - Payload bytes contain no magic byte and no schema ID prefix (US1 scenario 1)
  - Header name matches Apicurio convention for all 4 field/use_id combinations (FR-006)
  - Header value is `struct.pack(">q", id)` — 8 bytes big-endian signed (FR-007, SC-002)
  - `SchemaNotFoundError` raised before any bytes/headers produced (FR-008, US1 scenario 3)
  - 1 HTTP call for 1000 consecutive serializations (SC-005, NFR-001)

### Phase 4: Integration + Polish

- Byte-level round-trip: KAFKA_HEADERS payload + header can be decoded by Avro binary reader with schema (US1 scenario 4)
- CONFLUENT_PAYLOAD regression: serialize without `wire_format` argument produces bytes identical to pre-feature output (US2, SC-003)
- `WireFormat.CONFLUENT_PAYLOAD` explicit arg produces same output as default (US2 scenario 2)
- Type annotations complete, mypy strict passes
- Coverage gate: 100% line + branch

## KAFKA_HEADERS Header Specification (FR-006, FR-007)

See [research.md](research.md#D2-D3) for derivation. Summary:

| MessageField | use_id | Header name | Header value encoding |
|---|---|---|---|
| VALUE | "globalId" | `apicurio.registry.globalId` | `struct.pack(">q", global_id)` — 8 bytes |
| VALUE | "contentId" | `apicurio.registry.contentId` | `struct.pack(">q", content_id)` — 8 bytes |
| KEY | "globalId" | `apicurio.registry.key.globalId` | `struct.pack(">q", global_id)` — 8 bytes |
| KEY | "contentId" | `apicurio.registry.key.contentId` | `struct.pack(">q", content_id)` — 8 bytes |

## Requirements Traceability

| Requirement | Phase | Implementation |
|-------------|-------|----------------|
| FR-001 | Phase 1 | `WireFormat` enum in `serialization.py` |
| FR-002 | Phase 1 | `WireFormat` re-exported from `apicurio_serdes/__init__.py` |
| FR-003 | Phase 2 | `wire_format` param added to `AvroSerializer.__init__` |
| FR-004 | Phase 2 | `serialize()` CONFLUENT_PAYLOAD branch: framing unchanged |
| FR-005 | Phase 3 | `serialize()` KAFKA_HEADERS branch: raw Avro payload only |
| FR-006 | Phase 3 | Header name computed from `MessageField` × `use_id` table |
| FR-007 | Phase 3 | Header value: `struct.pack(">q", id)` — 8-byte big-endian signed long |
| FR-008 | Phase 3 | `SchemaNotFoundError` before bytes/headers for missing artifact |
| FR-009 | Phase 3 | `use_id` applies to KAFKA_HEADERS same as CONFLUENT_PAYLOAD |
| FR-010 | Phase 2+3 | `serialize()` method returning `SerializedMessage` (Option C) |
| NFR-001 | Phase 3 | Schema cache path unchanged — same cache key `(group_id, artifact_id)` |
| NFR-002 | Phase 3 | No new shared state; existing thread-safety guarantees preserved |
| SC-001 | Phase 3 | `AvroSerializer(wire_format=WireFormat.KAFKA_HEADERS).serialize(data, ctx)` |
| SC-002 | Phase 3+4 | Byte-level header test: `struct.pack(">q", id)` matches Java `ByteBuffer.putLong()` |
| SC-003 | Phase 4 | CONFLUENT_PAYLOAD regression test (byte-for-byte comparison) |
| SC-004 | Phase 1 | `WireFormat` importable from `apicurio_serdes` top-level |
| SC-005 | Phase 3+4 | Cache hit test: 1000 calls → 1 HTTP call in KAFKA_HEADERS mode |

## Complexity Tracking

No constitutional violations to justify. All decisions are aligned.
