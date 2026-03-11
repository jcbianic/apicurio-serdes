# ADR-005: Validate schema ID fits in 32 bits for CONFLUENT_PAYLOAD wire format

**Status:** Accepted
**Date:** 2026-03-11
**Context:** PR #32 commit `151f9d2`, Constitution Principle IV (Wire Format Fidelity)

## Context

The Confluent wire format packs schema IDs as unsigned 32-bit integers
(`struct.pack(">I", schema_id)`). Apicurio's `globalId` and `contentId` are
signed 64-bit values. When a schema ID exceeds 2^32-1, `struct.pack` raises
a cryptic `struct.error` with no actionable guidance.

## Decision

Validate the schema ID fits in unsigned 32-bit range before packing. On
failure, raise a `ValueError` with a clear message suggesting
`WireFormat.KAFKA_HEADERS` as an alternative that supports 64-bit IDs.

## Alternatives Considered

- **Silent truncation:** Rejected — would silently corrupt wire format,
  violating Principle IV.
- **Let `struct.error` propagate:** Rejected — the error message is opaque
  and gives no hint about wire format alternatives.
- **Always use 64-bit packing:** Rejected — would violate the Confluent wire
  format specification and break interoperability with Confluent consumers.

## Consequences

- Users hitting this limit get a clear error with a migration path.
- No silent data corruption.
- The `KAFKA_HEADERS` wire format supports full 64-bit IDs and is suggested
  in the error message.
