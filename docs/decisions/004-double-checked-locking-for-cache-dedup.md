# ADR-004: Double-checked locking for cache deduplication

**Status:** Accepted
**Date:** 2026-03-11
**Context:** PR #32 (NFR-001: concurrent first-time fetches produce exactly one HTTP request)

## Context

When multiple threads/coroutines concurrently request the same schema for the
first time, a naive implementation issues one HTTP request per caller (thundering
herd). The requirement is that exactly one HTTP request is made per cache miss,
regardless of concurrency.

## Decision

Use double-checked locking: check cache unlocked, acquire lock, re-check cache,
then fetch and populate.

```
if key in cache: return cache[key]       # fast path, no lock
with lock:
    if key in cache: return cache[key]   # lost-race check
    result = fetch(key)
    cache[key] = result
    return result
```

## Alternatives Considered

- **Always lock before checking cache:** Simpler, but adds lock contention on
  every cache hit — the common case after warm-up. Unacceptable for a hot path.
- **No locking:** Simpler, but allows thundering herd. Multiple concurrent
  cache misses for the same schema trigger multiple redundant HTTP requests.
- **`functools.lru_cache` or similar:** Does not support the async variant and
  does not give control over lock granularity.

## Consequences

- Cache hits (the common case) are lock-free.
- Cache misses serialize per-key, guaranteeing exactly one HTTP request.
- Sync client uses `threading.RLock`; async client uses `asyncio.Lock`.
  The lock type difference reflects the concurrency model, not an oversight.
