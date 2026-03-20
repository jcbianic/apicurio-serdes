# ADR-021: LRU + optional TTL cache eviction via `_CacheCore`

**Status:** Accepted
**Date:** 2026-03-19
**Supersedes:** [ADR-011](011-no-cache-eviction.md)
**Context:** Issue #39 (v0.4.0 milestone) — configurable LRU size cap and optional TTL expiry

## Context

ADR-011 accepted unbounded caches with a revisit trigger: *"if real-world users
report memory pressure, add optional `max_cache_size` with LRU eviction."*
Issue #39, added to the v0.4.0 milestone, activates that trigger.

Additionally, ADR-011's rationale that *"schemas are immutable"* is only
partially correct. ID-based lookups (`globalId`, `contentId`) are
content-addressed and truly immutable. But artifact-based lookups (`get_schema`
by `artifact_id`) return the **latest version**, which changes every time a new
schema version is registered. TTL is therefore justified for `_schema_cache` but
not for `_id_cache`.

## Decision

Introduce `_CacheCore` — a lock-free `OrderedDict`-backed cache class — in
`_base.py`. Replace both plain `dict` caches in `_RegistryClientBase` with
`_CacheCore` instances. Add two new keyword-only constructor parameters to both
`ApicurioRegistryClient` and `AsyncApicurioRegistryClient`:

| Parameter | Type | Default | Applied to |
| --------- | ---- | ------- | ---------- |
| `cache_max_size` | `int` | `1000` | Both `_schema_cache` and `_id_cache` |
| `cache_ttl_seconds` | `float \| None` | `None` | `_schema_cache` only |

`_id_cache` is always constructed with `ttl=None` regardless of
`cache_ttl_seconds`. `cache_max_size` applies to both caches as a memory bound.

## Rationale

### Split-cache TTL policy

Artifact-based lookups return the *latest version* (mutable). A new schema
version registered after a cache entry is written makes that entry stale. TTL
is the correct mechanism to surface new versions automatically.

ID-based lookups are content-addressed and immutable — `globalId` and
`contentId` are permanent identifiers for specific schema content. There is no
correctness reason to expire them; doing so only wastes HTTP round-trips to
re-fetch identical content.

### Intentional divergence from Apicurio Java

The Apicurio Java client (`ERCache.java`) applies the **same TTL** to all five
lookup indexes, including ID-based ones, and has **no LRU size cap**. We diverge
on both points as a deliberate semantic choice:

- **No TTL on ID cache**: ID lookups are immutable; expiring them is semantically
  wrong, not merely pragmatic.
- **LRU cap on both caches**: `ConcurrentHashMap` with no size limit is a memory
  safety hazard in long-running services. We cap both caches as a defensive bound.

### Alignment with Confluent Python

The Confluent Python client (`confluent-kafka-python`) independently arrived at
the same split: a permanent `_SchemaCache` for ID-based lookups and a
`TTLCache`/`LRUCache` for latest-version lookups. Our design aligns with
Confluent on semantics:

| Decision | Confluent Python | Apicurio Java | This library |
| -------- | ---------------- | ------------- | ------------ |
| TTL on artifact (mutable) cache | Yes (optional) | Yes (30 s default) | Yes (`None` default) |
| TTL on ID (immutable) cache | No — permanent | Yes (same TTL) | **No — permanent** |
| LRU cap on artifact cache | Yes (1000) | No | Yes (1000) |
| LRU cap on ID cache | No cap | No | Yes (1000, shared param) |

### Stdlib-only constraint

`_CacheCore` uses `collections.OrderedDict` and `time.monotonic` only — no new
dependencies. `move_to_end` and `popitem(last=False)` are both O(1) on CPython's
`OrderedDict`.

### Lock-free design

`_CacheCore` is intentionally lock-free. The existing client locks
(`threading.RLock` for sync, `asyncio.Lock` for async) already serialise the
check-fetch-set sequence required by the double-checked locking pattern
(ADR-004). Adding a second internal lock inside `_CacheCore` would introduce
re-entrancy concerns with `asyncio.Lock` (which is not re-entrant) and
unnecessary overhead.

`peek()` is used in the unlocked fast path: it checks TTL but does **not** call
`move_to_end` or `del` (both are mutating operations unsafe without a lock). The
actual LRU update and deletion happen inside the lock via `get()`.

### Default alignment

Defaults match Confluent Python exactly:

- `cache_max_size=1000` matches `cache.capacity` default.
- `cache_ttl_seconds=None` matches `cache.latest.ttl.sec` default (opt-in TTL).

## Consequences

- Both clients gain two new optional constructor parameters. The change is
  fully backward-compatible — existing code with no new kwargs gets
  `cache_max_size=1000` and `cache_ttl_seconds=None` (no TTL, same behaviour as
  before except with a 1000-entry LRU cap instead of unbounded growth).
- Memory growth is now bounded by `cache_max_size` entries in each cache.
- Users can opt into TTL by setting `cache_ttl_seconds`. After TTL elapses,
  the next `get_schema` call re-fetches from the registry and surfaces any
  new schema version automatically.
- `ValueError` is raised for `cache_max_size < 1` or `cache_ttl_seconds <= 0`
  (zero TTL is rejected; use `cache_ttl_seconds=None` to disable TTL).
