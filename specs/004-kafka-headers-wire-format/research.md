# Research: WireFormat.KAFKA_HEADERS Support

**Feature**: 004-kafka-headers-wire-format | **Date**: 2026-03-06

---

## D1: FR-010 — API Surface for Exposing Headers to the Caller

**Question**: How does `AvroSerializer` expose the Kafka message headers when `wire_format=WireFormat.KAFKA_HEADERS`?

**Options considered**:

| Option | Description | Problem |
|--------|-------------|---------|
| A | `__call__` returns `tuple[bytes, dict[str, bytes]]` in KAFKA_HEADERS mode | Return type becomes `bytes \| tuple[bytes, dict]` — breaks type safety, violates Constitution Principle I (API compatibility). Existing callers get a surprise at runtime. |
| B | `SerializationContext` gains a mutable `headers` attribute populated as a side effect | Requires removing `frozen=True` from the dataclass. Introduces invisible coupling — callers must inspect `ctx.headers` after calling the serializer. Hard to test. Not Pythonic. |
| C | New `serialize()` method returning `SerializedMessage(payload, headers)` | Fully additive. `__call__` contract unchanged for existing callers. Type-safe. IDE-discoverable. Testable in isolation. |

**Decision**: **Option C**.

**Rationale**: Option C is the only design that satisfies Principle I (zero change for CONFLUENT_PAYLOAD callers), Principle V (no new abstractions forced on existing users), and gives KAFKA_HEADERS users a clean, typed API. `__call__` delegates to `serialize()` internally and returns `.payload`, which for CONFLUENT_PAYLOAD is the framed bytes — byte-for-byte identical to current behavior.

**Constitution check**: ALIGNED. Additive public API. Existing `__call__` contract preserved.

---

## D2: KAFKA_HEADERS Header Naming Convention

**Question**: What header names does Apicurio Registry's native Java KAFKA_HEADERS serde use?

**Source**: Apicurio Registry v3 Java source, `io.apicurio.registry.serde.kafka.headers.KafkaSerdeHeaders` constants and `DefaultHeadersHandler` implementation (main branch).

**Findings**:

The header name constants defined in `KafkaSerdeHeaders` (Apicurio v3):

```java
String HEADER_KEY_GLOBAL_ID    = "apicurio.key.globalId";
String HEADER_VALUE_GLOBAL_ID  = "apicurio.value.globalId";
String HEADER_KEY_CONTENT_ID   = "apicurio.key.contentId";
String HEADER_VALUE_CONTENT_ID = "apicurio.value.contentId";
```

**Note**: Apicurio v2 used a different convention (`apicurio.registry.globalId`, `apicurio.registry.key.globalId`). The v3 convention is symmetric: `apicurio.{key|value}.{idType}`.

Mapping to Python `MessageField` × `use_id`:

| MessageField | use_id | Header name |
|---|---|---|
| VALUE | "globalId" | `apicurio.value.globalId` |
| VALUE | "contentId" | `apicurio.value.contentId` |
| KEY | "globalId" | `apicurio.key.globalId` |
| KEY | "contentId" | `apicurio.key.contentId` |

**Implementation**: A lookup table (dict or function) in `_serializer.py` mapping `(MessageField, use_id)` to the header name string. This keeps the logic declarative and testable.

**Constitution check**: ALIGNED with FR-006 and SC-002. Header names are Apicurio's native convention — not invented.

---

## D3: Header Value Byte Encoding

**Question**: How is the schema ID (integer) encoded in the Kafka header value bytes?

**Source**: Apicurio Registry Java source, `DefaultHeadersHandler.java`:

```java
ByteBuffer buff = ByteBuffer.allocate(8);
buff.putLong(globalId);
byte[] headerBytes = buff.array();
```

**Findings**:
- `ByteBuffer` default byte order is **big-endian** (matches Java's network byte order convention).
- `putLong()` writes a **64-bit signed integer** (Java `long` = 8 bytes).
- Python equivalent: `struct.pack(">q", schema_id)` — big-endian signed 8-byte integer.

**Why not `struct.pack(">I", schema_id)` (4-byte uint32 as in CONFLUENT_PAYLOAD)?**
- CONFLUENT_PAYLOAD uses `>I` (4-byte uint32) for the schema ID.
- KAFKA_HEADERS uses `>q` (8-byte int64) to match the Java native implementation.
- These two encodings differ intentionally — KAFKA_HEADERS headers are a separate wire contract from the CONFLUENT_PAYLOAD message prefix.

**IDs are always positive** in practice (registry-assigned), so signed vs unsigned does not affect real-world values. But to be byte-level compatible with the Java serde (`>q` signed), we use signed pack format.

**Constitution check**: ALIGNED with FR-007 (byte-level interoperability) and SC-002 (byte-level interop with native Java KAFKA_HEADERS serde).

---

## D4: Architecture Pattern — Conditional vs. Strategy

**Question**: Should KAFKA_HEADERS framing be implemented as a strategy object or a conditional branch in `serialize()`?

**Options considered**:

| Option | Description | Trade-off |
|--------|-------------|-----------|
| Strategy pattern | `WireFormatStrategy` ABC, two subclasses | Over-engineering for 2 variants. Adds 2 new classes + an interface for what is 5 lines of conditional logic. |
| Simple conditional | `if self.wire_format == WireFormat.KAFKA_HEADERS:` inside `serialize()` | Minimal. Easy to read and understand. Constitution Principle V explicitly mandates resisting scope creep. |

**Decision**: **Simple conditional in `serialize()`**.

**Rationale**: Constitution Principle V says "resist scope creep beyond that responsibility" and "A focused, minimal library is easier to audit, maintain, and trust. Users should be able to read and understand the full library in a single session." A strategy pattern is justified only when a third wire format arrives. Until then it is premature abstraction.

**Constitution check**: ALIGNED with Principle V.

---

## D5: WireFormat Placement

**Question**: In which module should `WireFormat` live?

**Options**: `serialization.py` alongside `MessageField` and `SerializationContext`, or a new `_wire_format.py`.

**Decision**: `serialization.py`.

**Rationale**: `WireFormat` is a serialization configuration enum — conceptually the same layer as `MessageField`. Creating a new module for a single 2-member enum violates Principle V (minimal footprint). `serialization.py` is the right home for all serialization configuration types.

---

## D6: `WireFormat` Top-Level Re-Export

**Question**: Must `WireFormat` be importable from `apicurio_serdes` top-level?

**Answer**: Yes. FR-002 and SC-004 both require `from apicurio_serdes import WireFormat` to work. This means adding `WireFormat` to `apicurio_serdes/__init__.py`'s imports and `__all__`.

---

## Tessl Tiles

No Tessl tiles queried for this feature. All technical decisions are based on:
- Apicurio Registry Java source code (header constants and encoding)
- Existing project plan (001-avro-serializer/plan.md) for technology stack continuity
- Python stdlib (`enum`, `dataclasses`, `struct`) for new symbols
