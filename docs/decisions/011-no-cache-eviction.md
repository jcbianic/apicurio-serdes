# ADR-011: No cache eviction — unbounded cache growth accepted

> **This decision has been superseded by [ADR-021](021-lru-ttl-cache-eviction.md).**
> ADR-021 introduces `_CacheCore` with LRU eviction and optional TTL, activated
> by issue #39 (v0.4.0 milestone). The analysis below is preserved for historical
> context.

**Status:** Superseded by [ADR-021](021-lru-ttl-cache-eviction.md)
**Date:** 2026-03-11
**Context:** PR #32 review item 11 — "Unbounded cache growth — no eviction"

## Context

The review flagged that all caches (`_schema_cache`, `_id_cache`,
`_parsed_cache`) grow monotonically with no TTL, LRU, or max-size limit.
In a long-running Kafka consumer encountering many distinct schemas over
time, memory grows without bound.

## Decision

Do not add cache eviction. Keep caches unbounded.

## Rationale

- In the target use case (Kafka consumers/producers), the number of distinct
  schemas is small and bounded by the number of topics/schemas in the
  organization. Typical deployments use tens of schemas, not millions.
- Each cached entry is tiny: a dict (schema), two ints (globalId, contentId).
  Even 10,000 schemas would consume negligible memory.
- Adding TTL or LRU introduces complexity (background timers, size tracking,
  eviction callbacks) and new failure modes (cache miss storms after
  eviction, stale schema served during TTL window).
- Schema content is immutable for a given contentId — a TTL would evict
  entries only to re-fetch identical data, wasting HTTP round-trips.
- If a user genuinely needs eviction (e.g., multi-tenant SaaS processing
  millions of schemas), they can create a new client instance periodically
  or wrap the client with their own eviction logic.

## Revisit Trigger

- If real-world users report memory pressure from cache growth, add an
  optional `max_cache_size` parameter with LRU eviction. Do not add TTL
  (schemas are immutable).
