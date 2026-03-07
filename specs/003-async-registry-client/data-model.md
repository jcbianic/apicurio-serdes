# Data Model: Async Registry Client

**Feature**: 003-async-registry-client | **Date**: 2026-03-07

## New Entities

### AsyncApicurioRegistryClient

Async registry accessor. Non-blocking counterpart to `ApicurioRegistryClient`. Holds connection configuration and a schema cache. Safe for concurrent use from multiple coroutines within the same event loop.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `url` | `str` | Yes | -- | Base URL of the Apicurio Registry v3 API |
| `group_id` | `str` | Yes | -- | Schema group applied to every lookup |
| `_http_client` | `httpx.AsyncClient` | Internal | -- | Async HTTP transport |
| `_schema_cache` | `dict[tuple[str, str], CachedSchema]` | Internal | `{}` | Maps `(group_id, artifact_id)` to resolved schema |
| `_lock` | `asyncio.Lock` | Internal | -- | Coroutine-safe mutex for cache population |

**Constructor validation** (FR-008):
- `url` must be non-empty → `ValueError("url must not be empty")`
- `group_id` must be non-empty → `ValueError("group_id must not be empty")`

**Methods**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_schema` | `async (artifact_id: str) -> CachedSchema` | Fetches schema by artifact ID. Caches on first call (FR-001, FR-002, FR-004). |
| `aclose` | `async () -> None` | Closes the underlying HTTP connection pool (FR-010). |
| `__aenter__` | `async () -> AsyncApicurioRegistryClient` | Context manager entry — returns self (FR-009). |
| `__aexit__` | `async (exc_type, exc_val, exc_tb) -> None` | Context manager exit — calls `aclose()` (FR-009). |

**get_schema call flow**:
1. Compute `cache_key = (self.group_id, artifact_id)`
2. Fast path: if `cache_key in self._schema_cache`, return cached value
3. Slow path: acquire `asyncio.Lock`
4. Inner check: if `cache_key in self._schema_cache`, return cached value (stampede prevention, NFR-001)
5. `await self._http_client.get(endpoint)` — async HTTP call
6. On `httpx.ConnectError`: raise `RegistryConnectionError` (FR-006)
7. On `status_code == 404`: raise `SchemaNotFoundError` (FR-005)
8. Parse response: `json.loads(response.text)`, extract `X-Registry-GlobalId`, `X-Registry-ContentId`
9. Build `CachedSchema`, store in `_schema_cache`, release lock, return

---

## Shared Entities (unchanged)

### CachedSchema

Imported from `apicurio_serdes._client`. Shared value object returned by both the sync and async clients (FR-003, SC-002).

| Field | Type | Description |
|-------|------|-------------|
| `schema` | `dict[str, Any]` | Parsed Avro schema (fastavro-ready Python dict) |
| `global_id` | `int` | Apicurio globalId from `X-Registry-GlobalId` header |
| `content_id` | `int` | Apicurio contentId from `X-Registry-ContentId` header |

---

## Relationships

```
AvroSerializer ──calls──→ ApicurioRegistryClient  (sync path)
                                    │
                                    └── _schema_cache: dict[(group_id, artifact_id), CachedSchema]
                                    └── _lock: threading.RLock

asyncio producer/consumer
        │
        └──→ AsyncApicurioRegistryClient  (async path, NEW)
                        │
                        ├── _schema_cache: dict[(group_id, artifact_id), CachedSchema]
                        ├── _lock: asyncio.Lock
                        └── _http_client: httpx.AsyncClient

Both clients ──return──→ CachedSchema (shared dataclass from _client.py)
```

---

## Validation Rules

| Entity | Rule | Source |
|--------|------|--------|
| `AsyncApicurioRegistryClient.url` | Must be non-empty string at construction | FR-008 |
| `AsyncApicurioRegistryClient.group_id` | Must be non-empty string at construction | FR-008 |
| Registry response | 404 → `SchemaNotFoundError` | FR-005 |
| Registry connection | `ConnectError` → `RegistryConnectionError` | FR-006 |

## State Transitions

### Async Schema Cache (per artifact_id)

```
[Empty] ──first await get_schema──→ [Fetching (lock held)]
                                           │
                         HTTP 200 ─────────┼──→ [Cached] ──subsequent calls──→ [Cached]
                                           │
                         HTTP 404 ─────────┼──→ SchemaNotFoundError (not cached)
                                           │
                         ConnectError ─────┴──→ RegistryConnectionError (not cached)
```

### Connection Lifecycle

```
[Created] ──await __aenter__──→ [Open]
                                   │
              ──await get_schema──→ [Open] (connection pool reused)
                                   │
              ──await aclose()─────┴──→ [Closed]
```

Once closed, calls to `get_schema` on a closed client will raise `httpx.RuntimeError` (httpx behaviour — not wrapped by the async client).
