# Research: Cache TTL and Eviction Policy (#39) (2026-03-19)

## Problem Statement

Both `_schema_cache` and `_id_cache` in `_RegistryClientBase` grow
unbounded for the lifetime of the client. Issue #39 asks for configurable
LRU size limits and optional TTL expiry, matching parity with Confluent
Python and Apicurio Java reference implementations.

## Requirements

Gathered through clarification dialogue:

- **Both** LRU size cap and TTL expiry, on both caches.
- **stdlib only** — no new dependencies (`collections.OrderedDict`,
  `time.monotonic`).
- **Eager TTL check** — expired entry treated as a miss on every `get`;
  no stale reads.
- Thread-safe under the existing double-checked locking pattern.

## Findings

### Relevant Files

| File | Purpose | Key Lines |
|------|---------|-----------|
| `src/apicurio_serdes/_base.py` | Cache declarations, `_RegistryClientBase` | 48–49, 67–96 |
| `src/apicurio_serdes/_client.py` | Sync cache access (get/write), `threading.RLock` | 71–85, 159–174, 181–194 |
| `src/apicurio_serdes/_async_client.py` | Async cache access, `asyncio.Lock` | 61–76, 148–163, 170–185 |
| `docs/decisions/011-no-cache-eviction.md` | ADR-011 — unbounded cache accepted | full |
| `docs/decisions/004-double-checked-locking-for-cache-dedup.md` | ADR-004 — stampede prevention | full |
| `tests/test_client.py` | TS-010/011/012 cache tests, double-check locking tests | 47–263, 399–434 |
| `tests/test_async_client.py` | Async cache + stampede tests | 142–195, 529–586 |

### Current Cache Structure

Both caches live in `_RegistryClientBase.__init__` (`_base.py:48–49`):

```python
self._schema_cache: dict[tuple[str, str], CachedSchema] = {}
self._id_cache: dict[tuple[str, int], dict[str, Any]] = {}
```

Key/value types:

| Cache | Key type | Value type | Mutability |
|-------|----------|------------|------------|
| `_schema_cache` | `(group_id, artifact_id)` | `CachedSchema` (frozen dataclass) | **Mutable** — latest version can change |
| `_id_cache` | `(id_type, id_value)` | `dict[str, Any]` | **Immutable** — globalId/contentId are permanent |

This distinction is load-bearing: `_schema_cache` entries can become stale
(a new schema version may be registered), whereas `_id_cache` entries are
content-addressed and never stale. Only `_schema_cache` truly needs TTL.

### Access Pattern (both clients)

Every lookup follows the same double-checked locking pattern (ADR-004):

```text
1. Fast-path check — outside lock, return immediately on hit
2. Acquire self._lock (RLock or asyncio.Lock)
3. Re-check inside lock — handle concurrent first-fetch
4. HTTP fetch
5. Write cache inside lock
```

All three methods (`get_schema`, `register_schema`, `_get_schema_by_id`)
use this pattern identically in both the sync and async clients.

### Existing Lock Types

| Client | Lock | Re-entrant? |
|--------|------|------------|
| `ApicurioRegistryClient` | `threading.RLock` | Yes |
| `AsyncApicurioRegistryClient` | `asyncio.Lock` | No |

The existing locks already guard the "check + fetch + set" sequence.
They are the correct place to also guard LRU bookkeeping, avoiding the
need for a second internal lock inside the cache object.

### ADR-011 (Must be Superseded)

ADR-011 (`docs/decisions/011-no-cache-eviction.md`) accepted unbounded
caches with the revisit trigger: *"if real-world users report memory
pressure, add optional `max_cache_size` with LRU eviction — do not add
TTL (schemas are immutable)."*

Issue #39, added to the v0.4.0 milestone, overrides this decision. A new
ADR-021 must supersede ADR-011.

Notably, ADR-011's rationale that *"schemas are immutable"* is only correct
for ID-based lookups. Artifact-based lookups (`get_schema` by artifact_id)
return the **latest version**, which can change when a new schema version is
registered. TTL is therefore justified for `_schema_cache` specifically.

### External Research — Sibling Repo Analysis

Source-verified against current HEAD of each repository.

**Confluent Python (`confluent-kafka-python`, `_sync/schema_registry_client.py`):**

Confluent uses a **split-cache architecture** — the most important finding
for our design:

| Lookup type | Cache class | TTL? | LRU cap? |
|-------------|-------------|------|---------|
| By schema ID / guid / subject+version | `_SchemaCache` (plain `defaultdict`) | **No** | **No** |
| Latest version by subject | `_latest_version_cache` (`cachetools.TTLCache` or `LRUCache`) | **Optional** | **Yes (1000)** |

Parameters (passed as config dict keys, not keyword args):

| Key | Default | Applied to |
|-----|---------|-----------|
| `"cache.capacity"` | `1000` | `_latest_version_cache` only |
| `"cache.latest.ttl.sec"` | `None` (no TTL) | `_latest_version_cache` only |

When `cache.latest.ttl.sec` is set, Confluent uses `cachetools.TTLCache`
(which is TTL + LRU combined). When it is `None`, it uses `cachetools.LRUCache`.
The immutable ID-based `_SchemaCache` has **no cap and no TTL** — it is permanent.
TTL checks are **eager** (`cachetools` behaviour).

**Apicurio Java (`schema-resolver/cache/ERCache.java`):**

Apicurio uses a **single unified `ERCache`** covering all five lookup indexes
(globalId, contentId, content hash, GAV, latest):

| Property | Default | Notes |
|----------|---------|-------|
| `apicurio.registry.check-period-ms` | `30000` (30 s) | Single TTL for all indexes |
| `apicurio.registry.cache-latest` | `true` | Disable caching of latest lookups only |
| `apicurio.registry.background-refresh-enabled` | `false` | Stale-while-revalidate; out of scope |

`ERCache` stores entries in plain `ConcurrentHashMap` instances — **no LRU
eviction and no size cap**. Expired entries remain in memory until accessed
and replaced. The Java client applies the same TTL to both mutable (latest)
and immutable (by ID) lookups — a pragmatic choice rather than a semantic one.
TTL checks are **eager** (`isExpired()` called on every `get()`).

**Alignment summary:**

| Decision | Confluent | Apicurio Java | Our proposal |
|----------|-----------|---------------|--------------|
| TTL on `_schema_cache` (mutable, latest) | Yes (optional) | Yes (30 s default) | Yes (`None` default) |
| TTL on `_id_cache` (immutable, by ID) | **No — permanent** | Yes (same TTL) | **Revised: No** |
| LRU cap on mutable cache | Yes (1000) | No | Yes (1000) |
| LRU cap on ID cache | **No cap** | No | Yes (1000, shared param) |
| Default TTL | `None` | 30 s | `None` |
| Default max_size | 1000 | ∞ | 1000 |
| Eager TTL check | Yes | Yes | Yes |

**Revised recommendation from sibling repo alignment:**
Confluent's split is semantically sounder and better justified: ID-based
lookups are content-addressed and immutable — there is no correctness
reason to ever expire them. Apply `cache_ttl_seconds` **only to
`_schema_cache`**. Apply `cache_max_size` to both (as a memory bound).

**Recommended defaults (revised):**

| Parameter | Default | Rationale |
|-----------|---------|-----------|
| `cache_max_size` | `1000` | Matches Confluent `cache.capacity` exactly |
| `cache_ttl_seconds` | `None` | Matches Confluent `cache.latest.ttl.sec`; opt-in |

**Python stdlib pattern (LRU + TTL with `OrderedDict`):**

```python
from collections import OrderedDict
import time

class _CacheCore:
    """Lock-free core — callers must serialise access."""

    _MISSING = object()

    def __init__(self, max_size: int, ttl: float | None) -> None:
        self._max_size = max_size
        self._ttl = ttl
        # Oldest (LRU) at front, most-recently-used at back.
        # Values: (stored_value, expiry) or (stored_value, None) when no TTL.
        self._store: OrderedDict = OrderedDict()

    def get(self, key):
        entry = self._store.get(key, self._MISSING)
        if entry is self._MISSING:
            return self._MISSING
        value, expiry = entry
        if expiry is not None and time.monotonic() >= expiry:
            del self._store[key]
            return self._MISSING
        self._store.move_to_end(key)  # bump to MRU
        return value

    def peek(self, key):
        """TTL check without LRU update — safe for unlocked fast-path."""
        entry = self._store.get(key, self._MISSING)
        if entry is self._MISSING:
            return self._MISSING
        value, expiry = entry
        if expiry is not None and time.monotonic() >= expiry:
            return self._MISSING  # expired; do NOT delete outside lock
        return value

    def set(self, key, value) -> None:
        expiry = time.monotonic() + self._ttl if self._ttl is not None else None
        if key in self._store:
            self._store[key] = (value, expiry)
            self._store.move_to_end(key)
        else:
            self._store[key] = (value, expiry)
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)  # evict LRU
```

Key points:

- `peek()` is for the **unlocked fast-path** — it checks TTL but does NOT
  call `move_to_end` or `del` (which are mutating operations unsafe without
  a lock). It returns `_MISSING` for expired entries; the actual deletion
  happens inside the lock on the next `get()` call.
- `get()` is for **inside the lock** — full LRU update and TTL eviction.
- `set()` is always called inside the lock.
- `time.monotonic()` (not `time.time()`) ensures TTL intervals are
  immune to NTP adjustments and clock jumps (PEP 418).
- `move_to_end` and `popitem(last=False)` are both O(1) on `OrderedDict`.

**Sync/async duality:**

`asyncio.Lock` cannot protect shared state from OS threads; conversely,
holding a `threading.RLock` across an `await` is safe but blocks the event
loop thread for the lock's hold time. Since cache operations are
pure-memory (microseconds), this is acceptable. The two clients already use
different lock types — `_CacheCore` (lock-free) integrates naturally into
both without an additional lock layer.

### Technical Constraints

1. **Double-checked locking must be preserved** — the fast-path `peek()` +
   locked `get()` sequence replaces the current `if key in cache:` checks.
2. **TTL for `_schema_cache` only** — `_id_cache` entries are immutable;
   applying TTL to them would re-fetch identical content needlessly.
   Confluent's reference implementation confirms this split: ID-based
   lookups are permanent, only mutable latest-version lookups get TTL.
   `cache_max_size` still applies to both caches as a memory bound.
3. **`asyncio.Lock` is not re-entrant** — `_CacheCore.get()` must not call
   `_CacheCore.set()` internally (no re-entrant paths) in the async client.
4. **100% test coverage required** — the `peek()` / expired-but-not-deleted
   path and the LRU eviction path both need explicit tests.
5. **ADR-011 superseded** — new ADR-021 required before implementation.
6. **Validation**: `cache_max_size >= 1`, `cache_ttl_seconds > 0` if not None.

## Open Questions

1. ~~**Single TTL for both caches or separate?**~~ **Resolved by sibling
   repo research.** Confluent explicitly applies TTL only to mutable
   latest-version lookups; ID-based lookups use a permanent cache.
   Our `cache_ttl_seconds` applies to `_schema_cache` only.
   `cache_max_size` applies to both as a memory bound.

2. **TTL = 0 semantics?**
   Should `cache_ttl_seconds=0` mean "no caching" or be rejected as
   invalid? Recommendation: raise `ValueError` (caching is a core feature;
   disabling it entirely is not the intended use).

3. **`max_size=0`?**
   Similarly, should `cache_max_size=0` be valid (disable LRU cap) or
   invalid? Recommendation: `ValueError` — the distinction between
   "bounded" and "unbounded" should be controlled by not passing the
   parameter rather than passing zero.

## Recommendations

### Architecture

Introduce `_CacheCore` in `_base.py`. Replace both plain `dict` caches in
`_RegistryClientBase` with `_CacheCore` instances. No change to the client
lock types; the existing locks already provide the necessary serialisation.

### New Constructor Parameters

Both `ApicurioRegistryClient` and `AsyncApicurioRegistryClient` gain:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cache_max_size` | `int` | `1000` | LRU cap applied to both caches |
| `cache_ttl_seconds` | `float \| None` | `None` | Per-entry TTL for `_schema_cache` only; `_id_cache` entries never expire |

### Fast-path Change

```python
# Before:
if cache_key in self._schema_cache:
    return self._schema_cache[cache_key]

# After:
cached = self._schema_cache.peek(cache_key)
if cached is not _MISSING:
    return cached
```

### Inside-lock Change

```python
# Before:
if cache_key in self._schema_cache:   # double-check
    return self._schema_cache[cache_key]

# After:
cached = self._schema_cache.get(cache_key)   # TTL-aware double-check
if cached is not _MISSING:
    return cached
```

### ADR Updates

- Create **ADR-021** superseding ADR-011; document the reversal rationale
  (issue #39 milestone v0.4.0, real user concern validated).
- Update **ADR-011** status to Superseded.

### Suggested `_CacheCore` location

Keep `_CacheCore` private in `_base.py` alongside `_RegistryClientBase`.
It is an implementation detail; no public export needed.
