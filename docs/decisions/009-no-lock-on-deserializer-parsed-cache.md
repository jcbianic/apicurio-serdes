# ADR-009: No lock on deserializer _parsed_cache

**Status:** Accepted
**Date:** 2026-03-11
**Context:** PR #32 review item 6 — "_parsed_cache is not thread-safe"

## Context

The review flagged that `AvroDeserializer._parsed_cache` (a plain dict) has
no synchronization. Two threads calling the deserializer simultaneously with
the same schema_id for the first time could both miss the cache and race on
the dict write. With free-threaded Python (PEP 703 / 3.13t), this could be
a proper data race.

## Decision

Do not add locking to the deserializer's `_parsed_cache`. Accept the benign
race under the GIL.

## Rationale

- Under CPython with the GIL (all current production deployments), dict
  assignment is atomic. The worst case is two threads both calling
  `fastavro.parse_schema()` for the same schema — a redundant but harmless
  computation. The second write overwrites the first with an identical value.
- Adding a lock to the deserializer hot path adds contention and complexity
  for a scenario (free-threaded Python) that is experimental and not yet
  targeted by this library.
- The registry client already deduplicates the HTTP fetch via double-checked
  locking. The parsed-schema cache is a CPU-only optimization, not a
  correctness concern under the GIL.

## Revisit Trigger

- When this library officially supports free-threaded Python (no-GIL),
  this decision must be revisited and a lock (or `concurrent.futures`-style
  dedup) added to `_parsed_cache`.
