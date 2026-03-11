# ADR-013: No additional top-level exports for serialization types

**Status:** Accepted
**Date:** 2026-03-11
**Context:** PR #32 review item 14 — "Incomplete top-level exports"

## Context

The review flagged that `__init__.py` exports `WireFormat` but not
`SerializationContext`, `MessageField`, or `SerializedMessage`. Similarly,
`AvroSerializer`, `AvroDeserializer`, and `AsyncAvroDeserializer` are not
top-level — users must import from `apicurio_serdes.avro`.

## Decision

Keep the current export surface. Do not promote serialization types or
Avro classes to the top-level `__init__.py`.

## Rationale

- The top-level exports are the "entry point" types: clients, errors, and
  `WireFormat` (needed at client construction time). These are what a user
  needs to get started.
- `SerializationContext`, `MessageField`, and `SerializedMessage` are
  serialization-specific types used only when calling the serializer. They
  belong in `apicurio_serdes.serialization`, which groups them by concern.
- `AvroSerializer` et al. are format-specific. When JSON or Protobuf
  serializers are added, the `apicurio_serdes.avro` namespace prevents
  naming collisions and keeps the top-level namespace clean.
- Promoting everything to the top level creates a flat namespace that
  becomes unwieldy as the library grows. The current two-level structure
  (`apicurio_serdes` for shared, `apicurio_serdes.avro` for Avro-specific)
  scales better.

## Consequences

- Users write `from apicurio_serdes.avro import AvroSerializer` and
  `from apicurio_serdes.serialization import SerializationContext`.
- Import paths are stable and won't change when new formats are added.
