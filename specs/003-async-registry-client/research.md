# Research: Async Registry Client

**Feature**: 003-async-registry-client | **Date**: 2026-03-07

## Decision Log

Decisions D1–D12 were established in features 001-avro-serializer and 002-avro-deserializer and carry forward unchanged. This feature adds D13–D17 for async-specific concerns.

### D13: Async HTTP Transport — httpx.AsyncClient

**Decision**: Use `httpx.AsyncClient` from the existing `httpx` runtime dependency.

**Rationale**:
- `httpx` was selected in D2 specifically because it provides both sync and async support in a single package
- `httpx.AsyncClient` is the async counterpart of `httpx.Client` — identical API, native asyncio support
- No new runtime dependency needed: `httpx.AsyncClient` ships with `httpx>=0.27.0`
- Eliminates the only viable alternative (aiohttp) without adding a new dep

**API pattern** (analogous to sync client):
```python
async with httpx.AsyncClient(base_url=url) as client:
    response = await client.get(endpoint)
```

Or with explicit lifecycle:
```python
client = httpx.AsyncClient(base_url=url)
response = await client.get(endpoint)
await client.aclose()
```

**Context manager support**: `httpx.AsyncClient` implements `__aenter__` / `__aexit__`, making it suitable for use inside the async client's own context manager.

**Connection lifecycle**: `aclose()` on `httpx.AsyncClient` closes the underlying connection pool. Failing to call it leaves open connections — this is why FR-009 (async context manager) and FR-010 (explicit `aclose()`) are required.

**Alternatives rejected**:
- `aiohttp`: Async-only. Would require a second HTTP library alongside `httpx.Client` for the sync client, violating DRY and Principle V (minimal footprint).
- `asyncio.open_connection`: Too low-level. Would require hand-rolling HTTP parsing, TLS, and connection pooling.

**Constitution check**: Principle V (no new runtime dependency justified): `httpx.AsyncClient` is bundled with `httpx` — no new package entry is added to `[project] dependencies`.

---

### D14: Async Cache Safety — asyncio.Lock with Double-Check Locking

**Decision**: Use `asyncio.Lock` with the same double-check locking pattern as the sync client's `threading.RLock`.

**Rationale**:
- `threading.RLock` blocks the OS thread — fatal in an asyncio event loop. It would freeze the entire event loop while waiting for a registry response.
- `asyncio.Lock` suspends only the waiting coroutine, yielding control back to the event loop during the wait period.
- The double-check locking pattern (check before lock, check again inside) prevents duplicate HTTP requests when multiple coroutines request the same uncached schema simultaneously (NFR-001: cache stampede prevention).

**Double-check locking pattern**:
```python
cache_key = (self.group_id, artifact_id)

# Fast path: cache hit without lock overhead
if cache_key in self._schema_cache:
    return self._schema_cache[cache_key]

# Slow path: acquire lock, re-check, fetch if still missing
async with self._lock:
    if cache_key in self._schema_cache:
        return self._schema_cache[cache_key]

    # ... fetch from registry ...
    self._schema_cache[cache_key] = cached
    return cached
```

**Why this prevents stampede**:
1. N coroutines simultaneously check the cache → all miss → all await the lock
2. First coroutine acquires lock, fetches schema, populates cache, releases lock
3. Remaining coroutines acquire lock one by one, find the cache populated on inner check, return immediately
4. Result: exactly 1 HTTP request for any given `artifact_id` (SC-003)

**asyncio.Lock vs threading.RLock**:
- `asyncio.Lock` is NOT reentrant (unlike `threading.RLock`). However, re-entrancy was never needed in the sync client's lock path — the lock wraps only the HTTP fetch + cache write, which is not recursive. So `asyncio.Lock` is a direct replacement.
- `asyncio.Lock()` must be created inside a running event loop OR lazily (Python 3.10+ allows creation at class instantiation time, the lock binds to the running loop on first use).

**Alternatives rejected**:
- `asyncio.Semaphore(1)`: Equivalent to Lock but with no semantic advantage here.
- Per-key locks: More granular but adds significant complexity (lock map management, cleanup) for marginal benefit in this use case.
- No lock (optimistic): Permits duplicate HTTP requests during simultaneous first-time fetches. Violates NFR-001.
- `threading.Lock` inside `asyncio.to_thread`: Unnecessarily complex thread delegation for a pure-async client.

**Constitution check**: Principle V (simplicity): double-check locking is the same proven pattern already used in the sync client. No new abstractions introduced.

---

### D15: Async Test Support — pytest-asyncio

**Decision**: Add `pytest-asyncio>=0.23.0` to `[dependency-groups] dev`.

**Rationale**:
- `pytest` does not natively run `async def` test functions — it requires a plugin
- `pytest-asyncio` is the de facto standard for async pytest support (15M+ monthly downloads)
- `respx` (already a dev dependency) supports async mocking of `httpx.AsyncClient` natively
- Version >=0.23.0 supports `asyncio_mode = "auto"` in `pyproject.toml` to avoid per-test `@pytest.mark.asyncio` decoration

**Configuration** (added to `pyproject.toml`):
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

This makes all `async def test_*` functions run automatically under asyncio without requiring explicit markers.

**Alternatives rejected**:
- `anyio` + `pytest-anyio`: `anyio` is already a transitive dependency of `httpx`, but `pytest-anyio` is less widely adopted and adds a compatibility layer that's unnecessary when we only target asyncio (not trio).
- `asynctest`: Unmaintained since 2021.
- `unittest.IsolatedAsyncioTestCase`: Incompatible with pytest-bdd and pytest fixtures.

**Constitution check**: Principle V (dependency justification): `pytest-asyncio` is a dev-only dependency required for async test execution. No stdlib alternative can run async test functions.

---

### D16: File Placement — _async_client.py

**Decision**: Create `src/apicurio_serdes/_async_client.py` alongside `_client.py`.

**Rationale**:
- Consistent naming convention: `_client.py` (sync), `_async_client.py` (async)
- Keeps related concerns co-located without merging sync and async logic into one file
- `CachedSchema` dataclass remains in `_client.py` and is imported by `_async_client.py` — single source of truth (FR-003)
- Clear module boundary: callers never import from `_async_client` directly; they use `from apicurio_serdes import AsyncApicurioRegistryClient`

**Alternatives rejected**:
- Merge into `_client.py`: Would create a large mixed sync/async file, complicating static analysis and readability.
- Separate sub-package (`apicurio_serdes/async/`): Over-engineered for a single class. Adds import path complexity.

---

### D17: ID-Based Methods — Excluded from Async MVP

**Decision**: `AsyncApicurioRegistryClient` does NOT expose `get_schema_by_global_id` or `get_schema_by_content_id` in the MVP.

**Rationale**:
- The spec (FR-001 through FR-011) does not mention ID-based methods. The feature scope is `get_schema(artifact_id)` only.
- The async client is an entry point for asyncio producers/consumers, who use `artifact_id` lookups (same as the sync client in the serializer path).
- ID-based lookups are a deserializer concern. An async deserializer (if ever needed) would be a separate feature.
- Following Principle V (resist scope creep): adding unrequested methods is explicitly prohibited.

**Future path**: If an async deserializer is later required, it would be specified as a new feature (e.g., 004-async-avro-deserializer) and would extend `AsyncApicurioRegistryClient` at that point.

## httpx.AsyncClient Usage Patterns

### Basic Async Fetch

```python
import httpx

async with httpx.AsyncClient(base_url="http://registry:8080/apis/registry/v3") as client:
    response = await client.get("/groups/my-group/artifacts/MySchema/versions/latest/content")
    response.raise_for_status()
    schema = response.json()
    global_id = int(response.headers["X-Registry-GlobalId"])
    content_id = int(response.headers["X-Registry-ContentId"])
```

### Explicit Lifecycle (no context manager)

```python
client = httpx.AsyncClient(base_url=url)
try:
    response = await client.get(endpoint)
finally:
    await client.aclose()
```

### Error Handling (same as sync client)

- `httpx.ConnectError` → `RegistryConnectionError`
- `response.status_code == 404` → `SchemaNotFoundError`
- Other non-2xx → `response.raise_for_status()` → `httpx.HTTPStatusError`

### respx Async Mocking

```python
import respx
import httpx
import pytest

@pytest.fixture
def mock_registry():
    with respx.mock(base_url="http://registry:8080") as mock:
        mock.get("/apis/registry/v3/groups/my-group/artifacts/MySchema/versions/latest/content").mock(
            return_value=httpx.Response(
                200,
                json={"type": "record", "name": "MySchema", "fields": []},
                headers={"X-Registry-GlobalId": "1", "X-Registry-ContentId": "1"},
            )
        )
        yield mock
```

`respx` intercepts both `httpx.Client` and `httpx.AsyncClient` requests transparently.
