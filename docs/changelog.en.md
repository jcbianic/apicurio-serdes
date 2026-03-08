# Changelog

All user-visible changes are documented here.

## 0.1.0 (unreleased)

### Added

- `ApicurioRegistryClient` — HTTP client for the Apicurio Registry v3 native API with schema caching and thread-safe access.
- `AvroSerializer` — serializes Python data to Confluent-framed Avro bytes. Supports custom `to_dict` hooks, `globalId`/`contentId` wire format selection, and strict mode.
- `SerializationContext` and `MessageField` — thin context objects compatible with confluent-kafka's interface.
- `SchemaNotFoundError`, `RegistryConnectionError`, `SerializationError` — typed exception hierarchy for predictable error handling.
