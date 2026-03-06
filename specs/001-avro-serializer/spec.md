# Feature Specification: Avro Serializer (Producer Side)

**Feature Branch**: `001-avro-serializer`
**Created**: 2026-03-06
**Status**: Draft
**Input**: User description: "Avro Serialization — the producer side end-to-end: ApicurioRegistryClient, AvroSerializer, SerializationContext, Confluent wire format (payload only)"

## User Stories *(mandatory)*

### User Story 1 - Serialize a Python dict to Confluent-framed Avro bytes (Priority: P1)

As a Python data engineer producing Kafka messages, I want to serialize a Python dict to Avro bytes using a schema stored in Apicurio Registry, so that my Kafka producer can send type-safe, schema-validated messages with no custom registry or encoding code at the call site.

**Why this priority**: This is the core end-to-end flow. Without it, no value is delivered. All other stories build on top of this one.

**Independent Test**: Can be fully tested by configuring a client and serializer against a live (or stub) registry, calling `serializer(dict, ctx)`, and verifying the output bytes have the correct Confluent wire framing and valid Avro payload.

**Acceptance Scenarios**:

1. **Given** a configured `ApicurioRegistryClient` pointing at a registry that holds a known Avro schema for a given artifact, **When** an `AvroSerializer` is created with that client and artifact ID and called with a valid dict and a `SerializationContext`, **Then** the returned bytes begin with magic byte `0x00` followed by a 4-byte schema identifier, followed by a valid Avro binary payload.

2. **Given** a configured serializer, **When** two different valid dicts conforming to the same schema are serialized, **Then** both produce valid Confluent-framed Avro bytes sharing the same 4-byte schema identifier prefix.

3. **Given** a configured serializer, **When** the serializer is called with a dict that is missing a field required by the schema, **Then** an error is raised before any bytes are produced.

---

### User Story 2 - Schema caching prevents redundant registry lookups (Priority: P2)

As a Python data engineer running a high-throughput Kafka producer, I want the Avro schema to be fetched from the registry once and reused for subsequent messages, so that my producer does not incur an HTTP round-trip on every serialization call.

**Why this priority**: A serializer that contacts the registry on every message is unusable in production. Caching is required for the feature to deliver real-world value.

**Independent Test**: Can be fully tested by serializing two messages with the same artifact ID and asserting the registry was contacted exactly once.

**Acceptance Scenarios**:

1. **Given** a configured `ApicurioRegistryClient`, **When** an `AvroSerializer` is called twice in sequence for the same artifact ID, **Then** the registry is contacted exactly once for that schema.

2. **Given** a client that has already fetched schema A, **When** an `AvroSerializer` for a different artifact B is used for the first time, **Then** the registry is contacted once for schema B, and schema A is not re-fetched.

---

### User Story 3 - Custom object-to-dict transformation via to_dict hook (Priority: P3)

As a Python developer whose message payloads are domain objects rather than plain dicts, I want to provide a custom conversion callable to `AvroSerializer`, so that I can serialize my existing objects without manually converting them at every call site.

**Why this priority**: The P1 story already serves users with plain dicts. This story reduces adoption friction for users with typed domain models without changing the core serialization path.

**Independent Test**: Can be fully tested by creating an `AvroSerializer` with a `to_dict` hook (e.g., `vars`) and serializing a simple object, verifying the output is identical to serializing the object's dict representation directly.

**Acceptance Scenarios**:

1. **Given** an `AvroSerializer` configured with a `to_dict` callable, **When** the serializer is called with a non-dict object, **Then** the callable is applied to the input first and the resulting dict is Avro-encoded normally.

2. **Given** an `AvroSerializer` configured without a `to_dict` callable, **When** the serializer is called with a plain dict, **Then** the dict is used directly for encoding with no transformation applied.

---

### Edge Cases

- What happens when the specified `artifact_id` does not exist in the registry?
- What happens when the registry is unreachable due to a network error?
- What happens when the input data contains extra fields not present in the schema?
- What happens when the input data is missing a field required by the schema?
- What happens when a provided `to_dict` callable raises an exception?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The library MUST provide an `ApicurioRegistryClient` that accepts a registry base URL and a `group_id`, and can retrieve Avro schema definitions from the registry by `artifact_id`.

- **FR-002**: The library MUST provide an `AvroSerializer` that accepts an `ApicurioRegistryClient` and an `artifact_id`, and serializes Python data to Avro-encoded bytes.

- **FR-003**: The output of `AvroSerializer` MUST conform to the Confluent wire format: magic byte `0x00`, followed by a 4-byte schema identifier, followed by the Avro binary payload. The default schema identifier is `globalId` (Apicurio 3.x default). See FR-010 for the configurable identifier option.

- **FR-013**: When the `to_dict` callable raises an exception, `AvroSerializer` MUST catch it and re-raise as a `SerializationError` that includes the original exception as its cause and identifies the failed conversion in its message.

- **FR-012**: `AvroSerializer` MUST accept an optional `strict` boolean parameter (default `False`). When `True`, extra fields in the input dict that are not present in the Avro schema MUST raise a `ValueError` before any bytes are produced. When `False`, extra fields are silently dropped.

- **FR-010**: `AvroSerializer` MUST accept an optional `use_id` parameter (default: `"globalId"`) that selects which registry-assigned identifier is embedded in the 4-byte wire format field. Accepted values are `"globalId"` and `"contentId"`. When `"globalId"` is selected the `X-Registry-GlobalId` response header value is used; when `"contentId"` is selected the `X-Registry-ContentId` response header value is used.

- **FR-004**: The library MUST provide a `SerializationContext` that carries the target Kafka topic name and a field indicator (KEY or VALUE).

- **FR-005**: `AvroSerializer` MUST be invocable as `serializer(data, ctx)` returning `bytes`.

- **FR-006**: `ApicurioRegistryClient` MUST cache retrieved schemas so that repeated serialization using the same `artifact_id` does not produce more than one registry request for that schema.

- **FR-007**: `AvroSerializer` MUST accept an optional `to_dict` callable; when provided, it is applied to the input before Avro encoding; when absent, the input is passed to the encoder unchanged.

- **FR-008**: When the referenced `artifact_id` is not found in the registry, `AvroSerializer` MUST raise a descriptive error that identifies the missing artifact.

- **FR-011**: When the Apicurio Registry is unreachable due to a network error, `ApicurioRegistryClient` MUST raise a `RegistryConnectionError` that wraps the underlying network exception and includes the registry URL in its message.

- **FR-009**: The `group_id` MUST be a required configuration parameter of `ApicurioRegistryClient` and MUST be applied to every schema lookup made by that client instance.

### Non-Functional Requirements

- **NFR-001**: `ApicurioRegistryClient` MUST be safe to use from multiple concurrent threads. Specifically, the schema cache MUST allow concurrent reads without data races, and concurrent cache population (first fetch for a given `artifact_id`) MUST not result in duplicate HTTP requests or cache corruption.

### Key Entities

- **ApicurioRegistryClient**: Registry accessor. Holds connection configuration (URL, group_id) and a schema cache. Responsible for all communication with the registry and for returning schema definitions by artifact identifier.

- **AvroSerializer**: Serializer. Holds a reference to an `ApicurioRegistryClient` and a target `artifact_id`. Accepts Python data and a `SerializationContext`, returns Confluent-framed Avro bytes.

- **SerializationContext**: Thin context object. Carries the Kafka topic name and a `MessageField` indicator used at serialization time.

- **MessageField**: Enumeration identifying whether the serialized datum is a Kafka message key (`KEY`) or value (`VALUE`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can produce a valid Confluent-framed Avro message to Kafka using only `ApicurioRegistryClient`, `AvroSerializer`, and `SerializationContext` — with no custom HTTP client or Avro library calls at the call site.

- **SC-002**: The bytes produced by `AvroSerializer` are byte-for-byte compatible with messages produced by Apicurio Registry's native Avro serializer given identical schema and input data.

- **SC-003**: Serializing 1,000 consecutive messages with the same schema results in exactly 1 registry HTTP call (schema cache hit on all subsequent calls).

- **SC-004**: Class names, method signatures, and configuration parameters mirror the `confluent-kafka` schema registry API where a direct analogue exists, verifiable by side-by-side comparison with the reference API.
