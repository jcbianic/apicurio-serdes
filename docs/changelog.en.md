# Changelog

All user-visible changes are documented here.

## Unreleased

### Added

- `ApicurioRegistryClient` and `AsyncApicurioRegistryClient` now retry automatically
  on transient failures. Retries on `httpx.TransportError` and HTTP 429/502/503/504
  with exponential backoff and full jitter. Three new constructor parameters control
  the behaviour: `max_retries` (default 3), `retry_backoff_ms` (default 1 000 ms),
  `retry_max_backoff_ms` (default 20 000 ms). Set `max_retries=0` to disable.
- Both clients accept an optional `http_client` escape hatch (`httpx.Client` /
  `httpx.AsyncClient`). When provided the supplied client is used as-is and is
  **not** closed by `close()` / `aclose()`. An `auth` parameter is also available
  for httpx-compatible authentication handlers when not using the escape hatch.
- `AvroDeserializer` and `AsyncAvroDeserializer` accept an optional
  `reader_schema` parameter (Avro schema dict, default `None`). When provided,
  fastavro performs Avro schema resolution between the writer schema (embedded
  in the message) and the supplied reader schema, enabling schema evolution
  patterns: field defaults fill gaps for added fields, type promotions, and
  alias-based field renames. Parsed once at construction time.
- `register_schema(artifact_id, schema, if_exists)` method on both
  `ApicurioRegistryClient` and `AsyncApicurioRegistryClient`. Registers a
  schema artifact via the Apicurio Registry v3 `POST /groups/{groupId}/artifacts`
  endpoint and populates the internal cache on success.
- `AvroSerializer` accepts three new optional constructor parameters:
  `schema` (Avro schema dict), `auto_register` (bool, default `False`), and
  `if_exists` (v3 `ifExists` policy). When `auto_register=True`, the first
  serialize call registers the schema automatically if the artifact is not
  found (HTTP 404).
- `SchemaRegistrationError` — new typed exception raised when the registry
  rejects a schema registration request (4xx/5xx response or missing JSON
  fields in the response body). Exported from the package root.
- `if_exists` values follow the Apicurio Registry v3 API: `"FAIL"`,
  `"FIND_OR_CREATE_VERSION"` (default), `"CREATE_VERSION"`.
- `QualifiedRecordIdStrategy` — new artifact resolver strategy. Derives the
  artifact ID from the Avro schema's record name and namespace:
  `"{namespace}.{name}"` when namespace is present, `"{name}"` otherwise.
  Matches the Confluent `RecordNameStrategy`. Raises `ValueError` at
  construction if the schema has no `"name"` field.
- `TopicRecordIdStrategy` — new artifact resolver strategy. Derives the
  artifact ID from the topic and the Avro schema's record name:
  `"{topic}-{namespace}.{name}"` when namespace is present,
  `"{topic}-{name}"` otherwise. Matches the Confluent
  `TopicRecordNameStrategy`. Raises `ValueError` at construction if the
  schema has no `"name"` field.

## 0.2.0 (2026-03-11)

### Client Hardening & Deduplication

This release focuses on improving robustness and maintainability through comprehensive
client hardening and code deduplication.

### Added

- `ApicurioRegistryClient` — HTTP client for the Apicurio Registry v3 native API
  with schema caching and thread-safe access.
- `AsyncApicurioRegistryClient` — async counterpart using `httpx.AsyncClient`, safe for concurrent coroutine use.
- `AvroSerializer` — serializes Python data to Confluent-framed Avro bytes. Supports
  custom `to_dict` hooks, `globalId`/`contentId` wire format selection, strict mode,
  and `KAFKA_HEADERS` wire format.
- `AvroDeserializer` — deserializes Confluent-framed Avro bytes back to Python dicts with optional `from_dict` hook.
- `AsyncAvroDeserializer` — async counterpart to `AvroDeserializer`.
- `SerializationContext` and `MessageField` — thin context objects compatible with confluent-kafka's interface.
- `WireFormat` enum — `CONFLUENT_PAYLOAD` and `KAFKA_HEADERS` framing modes.
- `SchemaNotFoundError`, `RegistryConnectionError`, `SerializationError`,
  `DeserializationError` — typed exception hierarchy for predictable error handling.
- `CachedSchema` — frozen (immutable) dataclass holding resolved schema data and registry metadata.
- Closed-client guard (`RuntimeError`) on both sync and async clients to prevent use-after-close.
- 32-bit schema ID validation for `CONFLUENT_PAYLOAD` wire format with actionable error message suggesting `KAFKA_HEADERS`.
- Signed int64 range validation on `globalId`/`contentId` from registry response headers.
- 19 Architecture Decision Records in `docs/decisions/`.

### Changed

- **Breaking**: `AvroDeserializer` and `AsyncAvroDeserializer` `use_id` default changed
  from `"contentId"` to `"globalId"` to match `AvroSerializer` default (see ADR-006).

### Internal

- Extracted `_RegistryClientBase` shared base class to deduplicate sync/async client logic (ADR-001).
- Double-checked locking pattern for thread-safe cache population (ADR-004).
- Removed stale `TECHNICAL_DEBT.md`.
