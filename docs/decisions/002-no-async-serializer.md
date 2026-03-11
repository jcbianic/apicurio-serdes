# ADR-002: No async serializer

**Status:** Accepted
**Date:** 2026-03-11
**Context:** PR #32 review discussion

## Context

The library provides both sync and async deserializers, but only a sync
serializer. During review, the question arose whether an async serializer
should be added for symmetry.

## Decision

Do not create an `AsyncAvroSerializer`. Keep serialization sync-only.

## Rationale

Serialization is primarily CPU-bound work (Avro encoding via fastavro). The
only I/O is the initial schema fetch on first call, which is cached. After
the first call, serialization is 100% CPU with zero I/O — async would add
overhead (event loop scheduling, coroutine creation) with no benefit.

Deserialization is different: a deserializer may encounter previously unseen
schema IDs on every call (cache miss scenario), making async I/O genuinely
useful for non-blocking registry lookups.

## Alternatives Considered

- **Add AsyncAvroSerializer for API symmetry:** Rejected because symmetry
  alone does not justify the maintenance cost and the misleading implication
  that serialization benefits from async.
- **Lazy async schema fetch in serializer:** Rejected because the schema is
  always known at serializer construction time (the user supplies the
  `artifact_id`), so eager caching on first call is sufficient.

## Consequences

- Users in async contexts can still use the sync serializer safely (it does
  no I/O after the first call).
- The async client exists and can be used directly for schema registration
  workflows if needed.
- If a genuine I/O-heavy serialization pattern emerges (e.g., schema
  evolution checks on every call), this decision should be revisited.
