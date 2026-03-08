# Public API Contract: Async Registry Client

**Feature**: 003-async-registry-client | **Date**: 2026-03-07

## Module Structure

```
apicurio_serdes/
  __init__.py              → exports: ApicurioRegistryClient, AsyncApicurioRegistryClient
  _client.py               → ApicurioRegistryClient, CachedSchema (unchanged)
  _async_client.py         → AsyncApicurioRegistryClient (NEW)
  _errors.py               → SchemaNotFoundError, RegistryConnectionError (unchanged)
```

## Import Paths (FR-011)

```python
from apicurio_serdes import AsyncApicurioRegistryClient
from apicurio_serdes import ApicurioRegistryClient  # unchanged
```

---

## AsyncApicurioRegistryClient

**Module**: `apicurio_serdes._async_client` (re-exported from `apicurio_serdes`)

```python
class AsyncApicurioRegistryClient:
    """Async HTTP client for the Apicurio Registry v3 native API.

    Non-blocking counterpart to ApicurioRegistryClient. Uses
    httpx.AsyncClient for async I/O. Safe for concurrent use
    from multiple coroutines within the same event loop.

    Args:
        url: Base URL of the Apicurio Registry v3 API.
             Example: "http://registry:8080/apis/registry/v3"
        group_id: Schema group identifier. Applied to every
                  schema lookup made by this client instance.

    Raises:
        ValueError: If url or group_id is empty.
    """

    def __init__(self, url: str, group_id: str) -> None: ...

    async def get_schema(self, artifact_id: str) -> CachedSchema:
        """Retrieve an Avro schema by artifact ID (async).

        Returns a cached result on subsequent calls for the same
        artifact_id. Safe for concurrent invocation: concurrent
        first-time fetches for the same artifact_id result in
        exactly one HTTP request (NFR-001).

        Args:
            artifact_id: The artifact identifier within the configured group.

        Returns:
            CachedSchema with parsed schema dict, global_id, and content_id.

        Raises:
            SchemaNotFoundError: If the artifact does not exist (HTTP 404).
            RegistryConnectionError: If the registry is unreachable.
        """
        ...

    async def aclose(self) -> None:
        """Close the underlying HTTP connection pool.

        Call this when the client is no longer needed and you are not
        using it as an async context manager. Safe to call multiple times.
        """
        ...

    async def __aenter__(self) -> "AsyncApicurioRegistryClient":
        """Enter the async context manager. Returns self."""
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit the async context manager. Calls aclose()."""
        ...
```

---

## CachedSchema (shared, from _client.py)

Unchanged. Returned by both `ApicurioRegistryClient.get_schema` and `AsyncApicurioRegistryClient.get_schema` (FR-003, SC-002).

```python
@dataclass
class CachedSchema:
    schema: dict[str, Any]   # Parsed Avro schema (fastavro-ready)
    global_id: int            # From X-Registry-GlobalId response header
    content_id: int           # From X-Registry-ContentId response header
```

---

## Error Types (unchanged from _errors.py)

| Error | Trigger | Attributes |
|-------|---------|------------|
| `SchemaNotFoundError` | HTTP 404 from registry | `group_id`, `artifact_id` |
| `RegistryConnectionError` | `httpx.ConnectError` | `url` |

```python
# SchemaNotFoundError raised by get_schema
try:
    cached = await client.get_schema("NonExistentArtifact")
except SchemaNotFoundError as e:
    print(e.group_id)    # "my-group"
    print(e.artifact_id) # "NonExistentArtifact"

# RegistryConnectionError raised by get_schema
try:
    cached = await client.get_schema("UserEvent")
except RegistryConnectionError as e:
    print(e.url)         # "http://registry:8080/apis/registry/v3"
```

---

## __init__.py Changes

```python
# Before (001-avro-serializer):
from apicurio_serdes._client import ApicurioRegistryClient
__all__ = ["ApicurioRegistryClient"]

# After (003-async-registry-client):
from apicurio_serdes._client import ApicurioRegistryClient
from apicurio_serdes._async_client import AsyncApicurioRegistryClient
__all__ = ["ApicurioRegistryClient", "AsyncApicurioRegistryClient"]
```

---

## Backward Compatibility

This change is **additive only**. No existing public API is modified:
- `ApicurioRegistryClient` signature and behaviour: unchanged
- `CachedSchema` dataclass: unchanged
- `__all__` in `apicurio_serdes.__init__`: extended (adding to `__all__` is backward compatible)

No MAJOR version bump required. This is a MINOR addition.
