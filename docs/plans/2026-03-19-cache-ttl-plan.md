# Plan: Cache TTL and Eviction Policy (#39) (2026-03-19)

## Summary

Replace the unbounded `dict` caches in `_RegistryClientBase` with a new
`_CacheCore` class backed by `collections.OrderedDict`. `_CacheCore` provides
LRU eviction (size cap) and optional TTL expiry using only stdlib. Two new
constructor parameters — `cache_max_size` (default `1000`) and
`cache_ttl_seconds` (default `None`) — are added to both clients. TTL applies
only to `_schema_cache` (mutable, latest-version lookups); `_id_cache` is
content-addressed and never expires. LRU cap applies to both caches. ADR-011
is superseded by ADR-021.

## Stakes Classification

**Level**: High

**Rationale**: Changes touch the cache abstraction shared by both sync and
async clients, the constructor signatures of both public client classes, and
the double-checked locking pattern (ADR-004). Incorrect mutation of
`OrderedDict` outside a lock would corrupt the LRU order. A regression here
silently degrades reliability under concurrent load.

## Context

**Research**: [docs/plans/2026-03-19-cache-ttl-research.md](2026-03-19-cache-ttl-research.md)

**Affected Areas**:

- `src/apicurio_serdes/_base.py` — `_CacheCore`, `_RegistryClientBase.__init__`
- `src/apicurio_serdes/_client.py` — `ApicurioRegistryClient.__init__`,
  cache access in `get_schema`, `register_schema`, `_get_schema_by_id`
- `src/apicurio_serdes/_async_client.py` — same methods, async versions
- `docs/decisions/021-lru-ttl-cache-eviction.md` — new ADR
- `docs/decisions/011-no-cache-eviction.md` — status updated to Superseded
- `docs/concepts/schema-caching.en.md` — updated cache lifetime and new eviction section
- `docs/concepts/schema-caching.fr.md` — French translation of same
- `docs/changelog.en.md` / `docs/changelog.fr.md` — `### Added` entries

## Success Criteria

- [ ] `_CacheCore` implements LRU eviction (O(1) via `OrderedDict`)
- [ ] `_CacheCore` implements optional per-entry TTL (eager check on every `get`/`peek`)
- [ ] `peek()` is safe to call outside a lock (no mutation)
- [ ] `get()` and `set()` are only called inside the existing client lock
- [ ] `cache_ttl_seconds` applies to `_schema_cache` only; `_id_cache` never expires
- [ ] `cache_max_size` applies to both caches
- [ ] Defaults match Confluent: `cache_max_size=1000`, `cache_ttl_seconds=None`
- [ ] `ValueError` raised for `cache_max_size < 1` or `cache_ttl_seconds <= 0`
- [ ] Double-checked locking pattern (ADR-004) preserved in both clients
- [ ] 100% test coverage; all existing tests pass
- [ ] ADR-021 created, ADR-011 updated to Superseded
- [ ] ADR-021 documents the intentional divergence from Apicurio Java
- [ ] `docs/concepts/schema-caching` updated (en + fr)
- [ ] Changelogs updated (en + fr)

## Implementation Steps

### Phase 1: ADR

#### Step 1.1: Create ADR-021

- **Files**: `docs/decisions/021-lru-ttl-cache-eviction.md`
- **Action**: Create a new ADR superseding ADR-011. Must cover:
  - The decision: `_CacheCore` with LRU cap on both caches, optional TTL on
    `_schema_cache` only
  - The revisit trigger from ADR-011 being met (issue #39, v0.4.0 milestone)
  - Stdlib-only constraint (`OrderedDict` + `time.monotonic`, no new deps)
  - The split-cache rationale: artifact-based lookups return the *latest
    version* (mutable); ID-based lookups are content-addressed (immutable)
  - **Intentional divergence from Apicurio Java**: The Java client applies the
    same TTL to all lookup indexes including ID-based ones, and has no LRU cap.
    We diverge on both points, aligning instead with Confluent Python: no TTL
    on ID-based lookups (re-fetching identical content is wasteful), and an LRU
    cap on both caches as a memory safety net. Document this as a deliberate
    semantic choice rather than a pragmatic simplification.
  - Default alignment with Confluent (`cache_max_size=1000`,
    `cache_ttl_seconds=None`)
- **Verify**: File exists, `markdownlint` passes
- **Complexity**: Small

#### Step 1.2: Update ADR-011 status

- **Files**: `docs/decisions/011-no-cache-eviction.md`
- **Action**: Change `**Status:** Accepted` to
  `**Status:** Superseded by [ADR-021](021-lru-ttl-cache-eviction.md)` and
  add a note at the top referencing the superseding decision.
- **Verify**: File opens, status line reads Superseded, `markdownlint` passes
- **Complexity**: Small

### Phase 2: `_CacheCore` — TDD

#### Step 2.1: Write `_CacheCore` unit tests (RED)

- **Files**: `tests/test_cache_core.py` (new file)
- **Action**: Write failing unit tests for `_CacheCore`. Tests must cover every
  behaviour path before any implementation exists.
- **Test cases**:

  *Basic get/set:*

  - `set("k", "v")` then `get("k")` → returns `"v"`
  - `get("missing")` on empty cache → returns `_CacheCore._MISSING`

  *TTL = None (no expiry):*

  - Entry set with `ttl=None` is never expired, even after simulated time
    advance (monkeypatch `time.monotonic`)
  - `peek("k")` with no TTL → returns value without modifying order

  *TTL > 0 (expiry):*

  - Entry still valid before TTL elapses → `get` and `peek` return value
  - Entry expired after TTL elapses (monkeypatch `time.monotonic`) →
    `get` returns `_MISSING` and deletes the entry from internal store
  - Entry expired → `peek` returns `_MISSING` but does NOT delete entry
    (store still contains the key after `peek`)
  - Entry overwritten via `set` resets the expiry timestamp

  *LRU eviction:*

  - `max_size=2`: insert `"a"`, `"b"`, `"c"` → `"a"` is evicted
  - `max_size=2`: insert `"a"`, `"b"`, access `"a"` (via `get`), insert
    `"c"` → `"b"` is evicted (LRU is `"b"` after `"a"` was accessed)
  - `max_size=2`: insert `"a"`, `"b"`, `peek("a")`, insert `"c"` →
    `"a"` is evicted (`peek` must NOT update LRU order)
  - Overwriting existing key does NOT evict (no size increase): insert
    `"a"`, `"b"`, `set("a", "new")` → both still present

  *Validation:*

  - `_CacheCore(max_size=0, ttl=None)` → `ValueError`
  - `_CacheCore(max_size=-1, ttl=None)` → `ValueError`
  - `_CacheCore(max_size=1, ttl=0)` → `ValueError`
  - `_CacheCore(max_size=1, ttl=-1.0)` → `ValueError`
  - `_CacheCore(max_size=1, ttl=None)` → valid (no TTL)
  - `_CacheCore(max_size=1, ttl=30.0)` → valid

- **Verify**: Tests exist and all fail (no implementation)
- **Complexity**: Medium

#### Step 2.2: Implement `_CacheCore` in `_base.py` (GREEN)

- **Files**: `src/apicurio_serdes/_base.py`
- **Action**: Add `_CacheCore` class before `_RegistryClientBase`. Add
  `from collections import OrderedDict` and `import time` to imports.
  Implement `__init__`, `get`, `peek`, `set` as specified in the research.
  `_MISSING = object()` at class level. Validate `max_size >= 1` and
  `ttl > 0 if ttl is not None` in `__init__`.
- **Verify**: All tests from Step 2.1 pass; `uv run pytest tests/test_cache_core.py`
  green; `uv run ruff check src/` clean
- **Complexity**: Small

### Phase 3: Wire `_CacheCore` into `_RegistryClientBase` and sync client — TDD

#### Step 3.1: Write constructor and validation tests (RED)

- **Files**: `tests/test_client.py`
- **Action**: Add BDD scenarios (or plain unit tests if simpler) for new
  constructor parameters and the updated cache behaviour in the sync client.
- **Test cases**:

  *Constructor validation:*

  - `ApicurioRegistryClient(..., cache_max_size=0)` → `ValueError`
  - `ApicurioRegistryClient(..., cache_max_size=-1)` → `ValueError`
  - `ApicurioRegistryClient(..., cache_ttl_seconds=0)` → `ValueError`
  - `ApicurioRegistryClient(..., cache_ttl_seconds=-1.0)` → `ValueError`
  - `ApicurioRegistryClient(..., cache_max_size=1, cache_ttl_seconds=30.0)`
    → constructs without error

  *LRU eviction (schema cache):*

  - Client with `cache_max_size=2`, three distinct artifact schemas →
    after fetching all three, first artifact requires a second HTTP call
    (was evicted); second and third are still cached

  *TTL expiry (schema cache only):*

  - Client with `cache_ttl_seconds=60` (monkeypatched clock) → `get_schema`
    after TTL elapsed triggers a new HTTP request
  - Client with `cache_ttl_seconds=60` → `get_schema` before TTL elapsed
    returns cached result without HTTP call

  *ID cache never expires (TTL does not apply):*

  - Client with `cache_ttl_seconds=60` (monkeypatched clock) →
    `get_schema_by_global_id` after TTL elapsed still returns cached
    result (no HTTP call); verifies split-cache TTL policy

  *Defaults:*

  - Default `cache_max_size` is `1000`
  - Default `cache_ttl_seconds` is `None`

- **Verify**: Tests exist and fail (no implementation change yet)
- **Complexity**: Medium

#### Step 3.2: Update `_RegistryClientBase.__init__` (GREEN partial)

- **Files**: `src/apicurio_serdes/_base.py:49–71`
- **Action**: Add `cache_max_size: int = 1000` and
  `cache_ttl_seconds: float | None = None` keyword-only params to
  `_RegistryClientBase.__init__`. Add validation (delegate to `_CacheCore`
  constructor). Replace:

  ```python
  self._schema_cache: dict[...] = {}
  self._id_cache: dict[...] = {}
  ```

  with:

  ```python
  self._schema_cache: _CacheCore = _CacheCore(
      max_size=cache_max_size, ttl=cache_ttl_seconds
  )
  self._id_cache: _CacheCore = _CacheCore(
      max_size=cache_max_size, ttl=None  # ID entries never expire
  )
  ```

- **Verify**: `uv run pytest` with no client method changes yet — tests that
  call `_schema_cache` / `_id_cache` directly will fail (expected); no
  import errors or syntax errors
- **Complexity**: Small

#### Step 3.3: Update `_client.py` cache access patterns (GREEN)

- **Files**: `src/apicurio_serdes/_client.py:65–90, 115–248`
- **Action**: Pass `cache_max_size` and `cache_ttl_seconds` through
  `ApicurioRegistryClient.__init__` to `super().__init__`. Replace all
  cache access patterns:

  Fast-path (outside lock), e.g. `_client.py:135`:

  ```python
  # Before:
  if cache_key in self._schema_cache:
      return self._schema_cache[cache_key]
  # After:
  cached = self._schema_cache.peek(cache_key)
  if cached is not _CacheCore._MISSING:
      return cached
  ```

  Inside-lock double-check (e.g. `_client.py:140–141`):

  ```python
  # Before:
  if cache_key in self._schema_cache:
      return self._schema_cache[cache_key]
  # After:
  cached = self._schema_cache.get(cache_key)
  if cached is not _CacheCore._MISSING:
      return cached
  ```

  Cache write (e.g. `_client.py:145`):

  ```python
  # Before:
  self._schema_cache[cache_key] = cached
  # After:
  self._schema_cache.set(cache_key, cached)
  ```

  Apply the same transformation to `register_schema` (`_client.py:219–231`)
  and `_get_schema_by_id` (`_client.py:234–248`, using `_id_cache`).

- **Verify**: `uv run pytest tests/test_client.py` — all existing cache tests
  plus new tests from Step 3.1 pass; `uv run ruff check src/` clean
- **Complexity**: Medium

### Phase 4: Wire `_CacheCore` into async client — TDD

#### Step 4.1: Write async constructor and cache behaviour tests (RED)

- **Files**: `tests/test_async_client.py`
- **Action**: Mirror the test cases from Step 3.1 for
  `AsyncApicurioRegistryClient`. All cases identical except async invocation
  with `await` and `pytest.mark.anyio`.
- **Test cases**: Same as Step 3.1 (constructor validation, LRU eviction,
  TTL expiry on schema cache, no TTL on ID cache, defaults)
- **Verify**: New async tests exist and fail
- **Complexity**: Medium

#### Step 4.2: Update `_async_client.py` cache access patterns (GREEN)

- **Files**: `src/apicurio_serdes/_async_client.py:50–74, 102–238`
- **Action**: Pass `cache_max_size` and `cache_ttl_seconds` through
  `AsyncApicurioRegistryClient.__init__` to `super().__init__`. Apply the
  same `peek()` / `get()` / `set()` transformation as Step 3.3 to:
  - `get_schema` (`_async_client.py:122–136`)
  - `register_schema` (`_async_client.py:205–220`)
  - `_get_schema_by_id` (`_async_client.py:222–238`)
- **Verify**: `uv run pytest tests/test_async_client.py` — all tests pass;
  `uv run ruff check src/` clean
- **Complexity**: Medium

### Phase 5: Full suite verification

#### Step 5.1: Run complete test suite

- **Files**: All test files
- **Action**: `uv run pytest` — must pass with 100% coverage; no regressions
- **Verify**: Zero failures, coverage 100%
- **Complexity**: Small

### Phase 6: Documentation

#### Step 6.1: Update English schema-caching concepts guide

- **Files**: `docs/concepts/schema-caching.en.md`
- **Action**: Make the following targeted changes:
  - **"Cache Lifetime" section**: Remove the sentence "There is no TTL
    (time-to-live) or expiration — once a schema is cached, it stays cached
    until the client is garbage-collected." Replace with an explanation that
    the lifetime is configurable: by default no expiry (same behaviour), but
    `cache_ttl_seconds` enables TTL on artifact-based lookups. Note that
    ID-based lookups never expire (content-addressed, immutable).
  - **"When to Create a New Client" section**: The bullet "If a schema changes
    in the registry and you need the new version" should be updated — with
    `cache_ttl_seconds` set, the running client will pick up new versions
    automatically after the TTL elapses; creating a new client is only needed
    when no TTL is configured.
  - **New section "Cache Eviction and Size Limits"**: Add after "Cache
    Lifetime". Explain `cache_max_size` (LRU eviction, applies to both caches,
    default 1000) and `cache_ttl_seconds` (TTL for artifact lookups only,
    default `None`). Include a short code example showing both params at
    construction time.
- **Verify**: `markdownlint docs/concepts/schema-caching.en.md` passes
- **Complexity**: Small

#### Step 6.2: Update French schema-caching concepts guide

- **Files**: `docs/concepts/schema-caching.fr.md`
- **Action**: Apply the same changes as Step 6.1 in French.
- **Verify**: `markdownlint docs/concepts/schema-caching.fr.md` passes
- **Complexity**: Small

#### Step 6.3: Update English changelog

- **Files**: `docs/changelog.en.md`
- **Action**: Add under `## Unreleased → ### Added`:

  ```markdown
  - `cache_max_size` (default `1000`) and `cache_ttl_seconds` (default `None`)
    constructor parameters on both clients. `cache_max_size` caps both caches
    with LRU eviction. `cache_ttl_seconds` enables optional TTL expiry on
    artifact-based lookups (`get_schema`, `register_schema`); ID-based lookups
    (`get_schema_by_global_id`, `get_schema_by_content_id`) are content-addressed
    and never expire.
  ```

- **Verify**: `markdownlint docs/changelog.en.md` passes
- **Complexity**: Small

#### Step 6.4: Update French changelog

- **Files**: `docs/changelog.fr.md`
- **Action**: Add the French translation of the entry from Step 6.3 under the
  corresponding `## Non publié → ### Ajouté` section.
- **Verify**: `markdownlint docs/changelog.fr.md` passes
- **Complexity**: Small

## Test Strategy

### Automated Tests

| Test Case | Type | Input | Expected Output |
| --------- | ---- | ----- | --------------- |
| `_CacheCore` get on empty cache | Unit | `get("k")` | `_MISSING` |
| `_CacheCore` set then get | Unit | `set("k","v")`, `get("k")` | `"v"` |
| `_CacheCore` TTL expired on `get` | Unit | set, advance clock past TTL, `get` | `_MISSING`, entry deleted |
| `_CacheCore` TTL expired on `peek` | Unit | set, advance clock past TTL, `peek` | `_MISSING`, entry NOT deleted |
| `_CacheCore` TTL valid on `peek` | Unit | set, clock before TTL, `peek` | value returned |
| `_CacheCore` `peek` does not update LRU | Unit | set a, b; `peek(a)`; set c | a evicted (LRU unchanged) |
| `_CacheCore` LRU eviction oldest | Unit | `max_size=2`; set a, b, c | a evicted |
| `_CacheCore` LRU eviction after `get` | Unit | `max_size=2`; set a, b; `get(a)`; set c | b evicted |
| `_CacheCore` no eviction on overwrite | Unit | `max_size=2`; set a, b; `set(a,"v2")` | both a, b present |
| `_CacheCore` `max_size=0` | Unit | `_CacheCore(max_size=0, ttl=None)` | `ValueError` |
| `_CacheCore` `ttl=0` | Unit | `_CacheCore(max_size=1, ttl=0)` | `ValueError` |
| `_CacheCore` `ttl=None` no expiry | Unit | set, advance clock by 1 hour, `get` | value returned |
| Sync client `cache_max_size=0` | Integration | constructor | `ValueError` |
| Sync client `cache_ttl_seconds=0` | Integration | constructor | `ValueError` |
| Sync client LRU eviction | Integration | `cache_max_size=2`, 3 schemas | 3rd fetch re-hits HTTP |
| Sync client TTL schema cache | Integration | `cache_ttl_seconds=60`, advance clock | re-hits HTTP after expiry |
| Sync client TTL id cache (no expiry) | Integration | `cache_ttl_seconds=60`, advance clock | ID lookup still cached |
| Async client constructor validation | Integration | same as sync | same errors |
| Async client LRU + TTL behaviour | Integration | same scenarios async | same expectations |

### Manual Verification

- [ ] Confirm `help(ApicurioRegistryClient)` shows `cache_max_size` and
  `cache_ttl_seconds` in the constructor docstring
- [ ] Confirm `help(AsyncApicurioRegistryClient)` shows the same params

## Risks and Mitigations

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| `OrderedDict.move_to_end` called outside lock corrupts LRU order | Data corruption under concurrent load | `peek()` explicitly excludes `move_to_end`; only `get()` calls it, and `get()` is always inside lock |
| `asyncio.Lock` is not re-entrant; nested lock acquire deadlocks | Hang under async concurrent load | `_CacheCore` is lock-free; no internal locking; existing single-level lock pattern preserved |
| TTL on `_id_cache` would re-fetch identical content | Wasted HTTP round-trips | `_id_cache` constructed with `ttl=None`; enforced in `_RegistryClientBase.__init__` |
| Monkeypatching `time.monotonic` in tests affects global state | Flaky tests from shared state | Use `unittest.mock.patch("apicurio_serdes._base.time.monotonic")` scoped to each test |
| `_CacheCore._MISSING` is module-level; comparison relies on identity | Accidental equality match | Sentinel is `object()`; identity check `is not _MISSING` is unambiguous |

## Rollback Strategy

All changes are additive at the API boundary (new optional kwargs with
defaults). Rolling back requires reverting `_base.py`, `_client.py`, and
`_async_client.py` to the prior dict-based implementation. No schema,
database, or wire-format changes are made. A `git revert` of the feature
commits is sufficient.

## Status

- [x] Plan approved
- [x] Implementation started
- [x] Implementation complete
