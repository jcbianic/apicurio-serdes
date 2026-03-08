# Feature Specification: Avro Deserializer (Consumer Side)

**Feature Branch**: `002-avro-deserializer`
**Created**: 2026-03-06
**Status**: Draft
**Input**: User description: "The MVP spec explicitly lists it alongside the serializer. It's the mirror piece: read Avro bytes, extract the contentId from the wire format, resolve the schema from the registry, deserialize to a Python dict. Without it, producers can't have working consumers."

## User Stories *(mandatory)*

### User Story 1 - Deserialize Confluent-framed Avro bytes to a Python dict (Priority: P1)

As a Python data engineer consuming Kafka messages, I want to deserialize Avro bytes into a Python dict using a schema resolved from the Apicurio Registry, so that my Kafka consumer receives structured, schema-validated data with no custom decoding or registry code at the call site.

**Why this priority**: This is the core end-to-end consumer flow. Without it, producers have no interoperable counterpart and the library is incomplete as an MVP. All other stories build on this one.

**Independent Test**: Can be fully tested by feeding Confluent-framed Avro bytes (magic byte + 4-byte schema ID + Avro payload) to an `AvroDeserializer` configured with a registry client, and verifying the returned dict matches the original data that was serialized.

**Acceptance Scenarios**:

1. **Given** a configured `ApicurioRegistryClient` and an `AvroDeserializer`, **When** the deserializer is called with valid Confluent-framed Avro bytes and a `SerializationContext`, **Then** it returns a Python dict whose contents match the original data that was serialized.

2. **Given** valid Confluent-framed Avro bytes whose 4-byte schema identifier corresponds to a known schema in the registry, **When** the deserializer is called, **Then** the schema is resolved from the registry using that identifier and used to decode the payload.

3. **Given** bytes that do not begin with the expected magic byte (`0x00`), **When** the deserializer is called, **Then** a descriptive error is raised before any registry lookup or decoding is attempted.

4. **Given** valid framing but a schema identifier that does not correspond to any schema in the registry, **When** the deserializer is called, **Then** a descriptive error is raised that identifies the unresolved identifier.

---

### User Story 2 - Schema caching prevents redundant registry lookups on deserialization (Priority: P2)

As a Python data engineer running a high-throughput Kafka consumer, I want schemas resolved during deserialization to be cached, so that processing a stream of messages sharing the same schema does not incur an HTTP round-trip per message.

**Why this priority**: A deserializer that contacts the registry on every message is unsuitable for production workloads. Without caching, latency accumulates and the registry becomes a bottleneck. This is essential for real-world value.

**Independent Test**: Can be fully tested by deserializing two messages carrying the same schema identifier and asserting the registry was contacted exactly once for that identifier.

**Acceptance Scenarios**:

1. **Given** an `AvroDeserializer`, **When** two messages sharing the same schema identifier are deserialized in sequence, **Then** the registry is contacted exactly once for that schema.

2. **Given** an `AvroDeserializer` whose cache already holds schema A, **When** a message carrying schema identifier B is deserialized for the first time, **Then** the registry is contacted once for schema B, and schema A is not re-fetched.

---

### User Story 3 - Custom dict-to-object transformation via from_dict hook (Priority: P3)

As a Python developer whose application works with typed domain objects rather than plain dicts, I want to provide a custom conversion callable to `AvroDeserializer`, so that deserialized data is automatically transformed into my domain objects without extra conversion code at every consumer call site.

**Why this priority**: The P1 story already delivers plain dict output for the majority of users. This story reduces adoption friction for teams using typed domain models without altering the core deserialization path.

**Independent Test**: Can be fully tested by creating an `AvroDeserializer` with a `from_dict` hook (e.g., a dataclass constructor), deserializing a message, and verifying the returned value is the expected domain object rather than a plain dict.

**Acceptance Scenarios**:

1. **Given** an `AvroDeserializer` configured with a `from_dict` callable, **When** the deserializer is called with valid Avro bytes, **Then** the callable is applied to the decoded dict and its return value is returned to the caller.

2. **Given** an `AvroDeserializer` configured without a `from_dict` callable, **When** the deserializer is called with valid Avro bytes, **Then** the decoded dict is returned directly with no transformation applied.

3. **Given** an `AvroDeserializer` configured with a `from_dict` callable that raises an exception, **When** the deserializer is called, **Then** a descriptive error is raised that includes the original exception as its cause and identifies the failed conversion in its message.

---

### Edge Cases

- What happens when the input bytes are empty or shorter than the minimum wire format frame (5 bytes)?
- What happens when the magic byte is present but the 4-byte identifier field is truncated?
- What happens when the schema identifier is valid but the Avro payload is corrupt or incompatible with the resolved schema?
- What happens when the registry is unreachable during schema resolution?
- What happens when the `from_dict` callable raises an exception?
- What happens when the deserialized dict contains fields not present in the schema (schema evolution scenario where the writer schema has extra fields)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The library MUST provide an `AvroDeserializer` that accepts an `ApicurioRegistryClient` and deserializes Confluent-framed Avro bytes into a Python dict.

- **FR-002**: `AvroDeserializer` MUST be invocable as `deserializer(data, ctx)` returning a Python dict (or the result of a `from_dict` hook if configured).

- **FR-003**: `AvroDeserializer` MUST read the magic byte and the 4-byte schema identifier from the input bytes before any decoding. If the magic byte is not `0x00`, it MUST raise a descriptive `DeserializationError` immediately.

- **FR-004**: `AvroDeserializer` MUST raise a descriptive `DeserializationError` when the input is fewer than 5 bytes, before any registry lookup.

- **FR-005**: `AvroDeserializer` MUST resolve the schema from the registry using the identifier extracted from the wire format before decoding the payload.

- **FR-006**: `AvroDeserializer` MUST accept an optional `use_id` parameter (default: `"contentId"`) that specifies which registry identifier type the 4-byte wire format field represents. Accepted values are `"globalId"` and `"contentId"`. The value must match the `use_id` setting used by the producer's `AvroSerializer`.

- **FR-007**: `ApicurioRegistryClient` MUST cache schemas resolved during deserialization so that repeated deserialization using the same schema identifier does not produce more than one registry request for that schema.

- **FR-008**: `AvroDeserializer` MUST accept an optional `from_dict` callable; when provided, it is applied to the decoded dict before the result is returned; when absent, the decoded dict is returned directly.

- **FR-009**: When the `from_dict` callable raises an exception, `AvroDeserializer` MUST catch it and re-raise as a `DeserializationError` that includes the original exception as its cause and identifies the failed conversion in its message.

- **FR-010**: When the schema identifier extracted from the wire format does not correspond to any schema in the registry, `AvroDeserializer` MUST raise a descriptive error that identifies the unresolved identifier.

- **FR-011**: When the Avro payload cannot be decoded using the resolved schema, `AvroDeserializer` MUST raise a descriptive `DeserializationError` that identifies the decoding failure.

- **FR-012**: When the Apicurio Registry is unreachable during schema resolution, `ApicurioRegistryClient` MUST raise a `RegistryConnectionError` that wraps the underlying network exception and includes the registry URL in its message.

### Non-Functional Requirements

- **NFR-001**: `AvroDeserializer` MUST be safe to use from multiple concurrent threads. Schema cache reads and writes MUST be free of data races and MUST NOT produce duplicate registry requests for the same identifier.

### Key Entities

- **AvroDeserializer**: Deserializer. Accepts an `ApicurioRegistryClient`. Reads wire-framed Avro bytes, resolves the schema by identifier, decodes the payload, and returns a Python dict (or a transformed object via `from_dict`).

- **ApicurioRegistryClient**: Registry accessor (shared with the serializer feature). Holds connection configuration and a schema cache. Used by `AvroDeserializer` to resolve schemas by their wire-format identifier.

- **SerializationContext**: Thin context object (shared with the serializer feature). Carries the Kafka topic name and a `MessageField` indicator used at deserialization time.

- **MessageField**: Enumeration (shared with the serializer feature). Identifies whether the deserialized datum is a Kafka message key (`KEY`) or value (`VALUE`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can consume and decode a valid Confluent-framed Avro message from Kafka using only `ApicurioRegistryClient`, `AvroDeserializer`, and `SerializationContext` — with no custom HTTP client or Avro library calls at the call site.

- **SC-002**: The dict produced by `AvroDeserializer` from bytes generated by `AvroSerializer` (with identical schema and input data) equals the original input dict — round-trip fidelity is verifiable by a single equality assertion.

- **SC-003**: Deserializing 1,000 consecutive messages sharing the same schema identifier results in exactly 1 registry HTTP call (schema cache hit on all subsequent calls).

- **SC-004**: `AvroDeserializer`'s class name, method signature, and configuration parameters mirror the `confluent-kafka` schema registry API where a direct analogue exists, verifiable by side-by-side comparison with the reference API.

- **SC-005**: A round-trip test — serialize a Python dict with `AvroSerializer`, then deserialize the result with `AvroDeserializer` — passes without any manual registry interaction between the two steps.
