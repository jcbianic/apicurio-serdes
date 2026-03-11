# Changelog

All user-visible changes are documented here.

## 0.2.0 (2026-03-11)

### Client Hardening & Deduplication

This release focuses on improving robustness and maintainability through comprehensive client hardening and code deduplication.

### Added

- `ApicurioRegistryClient` — HTTP client for the Apicurio Registry v3 native API with schema caching and thread-safe access.
- `AsyncApicurioRegistryClient` — async counterpart using `httpx.AsyncClient`, safe for concurrent coroutine use.
- `AvroSerializer` — serializes Python data to Confluent-framed Avro bytes. Supports custom `to_dict` hooks, `globalId`/`contentId` wire format selection, strict mode, and `KAFKA_HEADERS` wire format.
- `AvroDeserializer` — deserializes Confluent-framed Avro bytes back to Python dicts with optional `from_dict` hook.
- `AsyncAvroDeserializer` — async counterpart to `AvroDeserializer`.
- `SerializationContext` and `MessageField` — thin context objects compatible with confluent-kafka's interface.
- `WireFormat` enum — `CONFLUENT_PAYLOAD` and `KAFKA_HEADERS` framing modes.
- `SchemaNotFoundError`, `RegistryConnectionError`, `SerializationError`, `DeserializationError` — typed exception hierarchy for predictable error handling.
- `CachedSchema` — frozen (immutable) dataclass holding resolved schema data and registry metadata.
- Closed-client guard (`RuntimeError`) on both sync and async clients to prevent use-after-close.
- 32-bit schema ID validation for `CONFLUENT_PAYLOAD` wire format with actionable error message suggesting `KAFKA_HEADERS`.
- Signed int64 range validation on `globalId`/`contentId` from registry response headers.
- 19 Architecture Decision Records in `docs/decisions/`.

### Changed

- **Breaking**: `AvroDeserializer` and `AsyncAvroDeserializer` `use_id` default changed from `"contentId"` to `"globalId"` to match `AvroSerializer` default (see ADR-006).

### Internal

- Extracted `_RegistryClientBase` shared base class to deduplicate sync/async client logic (ADR-001).
- Double-checked locking pattern for thread-safe cache population (ADR-004).
- Removed stale `TECHNICAL_DEBT.md`.
