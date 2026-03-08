# Feature Specification: WireFormat.KAFKA_HEADERS Support

**Feature Branch**: `004-kafka-headers-wire-format`
**Created**: 2026-03-06
**Status**: Draft
**Input**: User description: "004 — WireFormat.KAFKA_HEADERS support. The intent doc lists KAFKA_HEADERS as the second wire format option alongside CONFLUENT_PAYLOAD. Currently the wire format is likely only stubbed or partially handled. This is a clean, bounded feature: instead of embedding the schema ID in the message bytes, it goes in Kafka message headers — an important deployment pattern in some Apicurio setups."

## User Stories *(mandatory)*

### User Story 1 - Serialize using KAFKA_HEADERS wire format (Priority: P1)

As a Python data engineer working with an Apicurio Registry deployment configured for KAFKA_HEADERS wire format, I want to serialize Avro messages where the schema identifier is placed in Kafka message headers rather than embedded in the message bytes, so that my Kafka messages remain payload-clean and interoperate with other producers and consumers using the same Apicurio KAFKA_HEADERS convention.

**Why this priority**: This is the core capability of the feature. Without it, users who operate in KAFKA_HEADERS environments have no path to produce interoperable messages.

**Independent Test**: Can be fully tested by configuring a serializer with `WireFormat.KAFKA_HEADERS`, serializing a dict, and verifying (a) the returned bytes are pure Avro binary with no magic byte or schema ID prefix, and (b) the schema identifier is accessible as a Kafka-compatible header value.

**Acceptance Scenarios**:

1. **Given** an `AvroSerializer` configured with `WireFormat.KAFKA_HEADERS`, **When** the serializer is called with a valid dict and a `SerializationContext`, **Then** the returned bytes contain only the raw Avro binary payload — no magic byte and no 4-byte schema identifier prefix.

2. **Given** an `AvroSerializer` configured with `WireFormat.KAFKA_HEADERS`, **When** the serializer is called with a valid dict and a `SerializationContext`, **Then** the schema identifier (globalId or contentId, depending on `use_id`) is made available to the caller as a Kafka message header value, using Apicurio's native header naming convention for the given field type (KEY or VALUE).

3. **Given** an `AvroSerializer` configured with `WireFormat.KAFKA_HEADERS`, **When** the serializer is called with a dict that is missing a field required by the schema, **Then** an error is raised before any bytes are produced and no headers are set.

4. **Given** an `AvroSerializer` configured with `WireFormat.KAFKA_HEADERS`, **When** the raw bytes produced are decoded by an Apicurio-native deserializer using the headers as the schema identifier source, **Then** the decoded record is identical to the original input data.

---

### User Story 2 - CONFLUENT_PAYLOAD remains the default, unaffected by the new option (Priority: P2)

As a Python data engineer already using `AvroSerializer` with Confluent wire format, I want my existing code to continue working without any changes after the KAFKA_HEADERS option is introduced, so that adopting the new version does not require a migration.

**Why this priority**: API compatibility (Constitution Principle I) requires that existing users see zero behavior change. Any regression in the default path is a breaking change.

**Independent Test**: Can be fully tested by running existing CONFLUENT_PAYLOAD serialization tests without any code changes, verifying that output bytes still begin with magic byte `0x00` followed by the 4-byte schema identifier.

**Acceptance Scenarios**:

1. **Given** an `AvroSerializer` configured without an explicit `wire_format` parameter, **When** the serializer is called with a valid dict, **Then** the returned bytes begin with magic byte `0x00` followed by a 4-byte big-endian schema identifier — identical to the current behavior.

2. **Given** an `AvroSerializer` configured explicitly with `WireFormat.CONFLUENT_PAYLOAD`, **When** the serializer is called with a valid dict, **Then** the output is identical to the output produced with no `wire_format` argument.

---

### User Story 3 - Wire format is an explicit, named option at configuration time (Priority: P3)

As a Python developer configuring serializers for a Kafka pipeline, I want to select the wire format using a named constant (e.g., `WireFormat.KAFKA_HEADERS`) rather than a string or boolean flag, so that my configuration is self-documenting, discoverable by IDE tooling, and protected against typos.

**Why this priority**: Usability improvement that reduces misconfiguration risk. The core capability (US1) could ship without this, but the API would be less ergonomic and harder to extend in the future.

**Independent Test**: Can be fully tested by importing `WireFormat` from the library's public API, verifying it exposes at least `CONFLUENT_PAYLOAD` and `KAFKA_HEADERS` members, and that passing either to `AvroSerializer` produces the expected behavior.

**Acceptance Scenarios**:

1. **Given** the `WireFormat` enum is importable from the library's public API, **When** a developer configures `AvroSerializer(wire_format=WireFormat.KAFKA_HEADERS)`, **Then** no `TypeError` or `ValueError` is raised and the serializer uses KAFKA_HEADERS mode.

2. **Given** the `WireFormat` enum, **When** a developer's IDE performs autocompletion on `WireFormat.`, **Then** both `CONFLUENT_PAYLOAD` and `KAFKA_HEADERS` members appear as valid options.

---

### Edge Cases

- What happens when a consumer receives a KAFKA_HEADERS-formatted message but expects CONFLUENT_PAYLOAD framing (or vice versa)?
- What happens when the Kafka message headers are missing the schema identifier on the consumer side?
- What happens when `use_id="contentId"` is combined with `WireFormat.KAFKA_HEADERS` — is the contentId placed in the header correctly?
- What happens when an invalid value is passed as `wire_format` to `AvroSerializer`?
- What happens when the schema identifier cannot be resolved from the registry in KAFKA_HEADERS mode?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The library MUST expose a `WireFormat` enum with at least two members: `CONFLUENT_PAYLOAD` and `KAFKA_HEADERS`.

- **FR-002**: `WireFormat` MUST be importable from the library's top-level public API.

- **FR-003**: `AvroSerializer` MUST accept a `wire_format` parameter of type `WireFormat`, defaulting to `WireFormat.CONFLUENT_PAYLOAD`.

- **FR-004**: When `wire_format=WireFormat.CONFLUENT_PAYLOAD`, `AvroSerializer` MUST produce output bytes with the existing framing: magic byte `0x00`, followed by a 4-byte big-endian schema identifier, followed by the Avro binary payload. This MUST be identical to the current behavior.

- **FR-005**: When `wire_format=WireFormat.KAFKA_HEADERS`, `AvroSerializer` MUST produce output bytes that are the raw Avro binary payload only, with no magic byte prefix and no schema identifier prefix.

- **FR-006**: When `wire_format=WireFormat.KAFKA_HEADERS`, the schema identifier MUST be communicated to the caller alongside the payload bytes. The header name MUST follow Apicurio Registry's native KAFKA_HEADERS naming convention, differentiating between KEY and VALUE fields (via `SerializationContext.field`) and between `globalId` and `contentId` (via the `use_id` parameter).

- **FR-007**: The schema identifier header value in KAFKA_HEADERS mode MUST be encoded in a format that is byte-level interoperable with messages produced by Apicurio Registry's native Java KAFKA_HEADERS serde.

- **FR-008**: When `wire_format=WireFormat.KAFKA_HEADERS` and the artifact does not exist in the registry, `AvroSerializer` MUST raise a `SchemaNotFoundError` identifying the missing artifact — no bytes and no headers MUST be returned.

- **FR-009**: The `use_id` parameter (`"globalId"` or `"contentId"`) MUST apply to both wire format modes — it selects which registry-assigned identifier is used, regardless of whether that identifier is transmitted in the payload prefix or in message headers.

- **FR-010**: When `wire_format=WireFormat.KAFKA_HEADERS`, the API MUST surface the schema identifier header(s) to the caller via a dedicated `serialize()` method that returns a `SerializedMessage` dataclass with `payload: bytes` and `headers: dict[str, bytes]` fields. The existing `__call__` method remains backward-compatible, returning only the payload bytes (headers discarded when KAFKA_HEADERS mode invoked through `__call__`). See plan.md§"FR-010 Resolution" for detailed rationale.

### Non-Functional Requirements

- **NFR-001**: Adding KAFKA_HEADERS support MUST NOT increase the number of HTTP calls to the registry. Schema caching MUST be preserved across both wire format modes.

- **NFR-002**: The KAFKA_HEADERS mode MUST be thread-safe under the same conditions as the existing CONFLUENT_PAYLOAD mode.

### Key Entities

- **WireFormat**: Enumeration of supported wire format modes. Defines whether the schema identifier is embedded in the message bytes (`CONFLUENT_PAYLOAD`) or communicated via Kafka message headers (`KAFKA_HEADERS`).

- **AvroSerializer**: Extended with a `wire_format` parameter. Delegates framing behaviour to the selected wire format strategy.

- **SerializationContext**: Carries the Kafka topic name and `MessageField` indicator. In KAFKA_HEADERS mode, the `MessageField` value determines the correct header name prefix (`key` vs `value`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can produce a valid KAFKA_HEADERS-formatted Avro message by configuring `AvroSerializer(wire_format=WireFormat.KAFKA_HEADERS)` — no custom header construction code at the call site.

- **SC-002**: The payload bytes and headers produced by `AvroSerializer` in KAFKA_HEADERS mode are byte-level interoperable with messages produced by Apicurio Registry's native Java KAFKA_HEADERS Avro serializer, given identical schema and input data.

- **SC-003**: An `AvroSerializer` created without a `wire_format` argument produces output bytes that are byte-for-byte identical to those produced before this feature was introduced (zero regression on the default path).

- **SC-004**: `WireFormat` is importable from the library's top-level namespace (`from apicurio_serdes import WireFormat`) and is discoverable via IDE autocompletion with at least `CONFLUENT_PAYLOAD` and `KAFKA_HEADERS` members.

- **SC-005**: Serializing 1,000 consecutive messages with `WireFormat.KAFKA_HEADERS` results in exactly 1 registry HTTP call (schema caching guarantee preserved for the new mode).

## Clarifications

### Session 2026-03-08

- **Q: FR-010 — How does the API surface headers to the caller in KAFKA_HEADERS mode?**
  **A: Option C — Dedicated `serialize()` method returns `SerializedMessage(payload: bytes, headers: dict[str, bytes])` dataclass. Existing `__call__` remains backward-compatible.**
  **Rationale**: Fully additive API (no breaking changes), explicit semantics, type-safe, aligns with Constitution Principle I (API compatibility).
  **References**: [FR-010], [plan.md§FR-010-Resolution]
