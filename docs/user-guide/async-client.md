# Async Registry Client

`AsyncApicurioRegistryClient` is the async counterpart to
`ApicurioRegistryClient`. It uses `httpx.AsyncClient` for non-blocking
HTTP communication with the Apicurio Registry v3 API.

## Basic Usage

```python
from apicurio_serdes import AsyncApicurioRegistryClient

client = AsyncApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="my-group",
)

cached = await client.get_schema("UserEvent")
print(cached.schema)      # Parsed Avro schema dict
print(cached.global_id)   # Registry globalId
print(cached.content_id)  # Registry contentId
```

## Context Manager

Use `async with` to ensure the underlying HTTP connection pool is closed
when you are done:

```python
async with AsyncApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="my-group",
) as client:
    cached = await client.get_schema("UserEvent")
# Connection pool is closed here
```

If you are not using a context manager, call `aclose()` explicitly:

```python
client = AsyncApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="my-group",
)
try:
    cached = await client.get_schema("UserEvent")
finally:
    await client.aclose()
```

## FastAPI Lifespan Integration

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from apicurio_serdes import AsyncApicurioRegistryClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncApicurioRegistryClient(
        url="http://registry:8080/apis/registry/v3",
        group_id="my-group",
    ) as client:
        app.state.registry = client
        yield


app = FastAPI(lifespan=lifespan)


@app.post("/produce")
async def produce(request):
    client = request.app.state.registry
    cached = await client.get_schema("UserEvent")
    # Use cached.schema for serialization...
```

## Sync vs Async Comparison

| Feature | Sync | Async |
|---------|------|-------|
| Class | `ApicurioRegistryClient` | `AsyncApicurioRegistryClient` |
| Schema fetch | `client.get_schema(id)` | `await client.get_schema(id)` |
| Schema registration | `client.register_schema(id, schema)` | `await client.register_schema(id, schema)` |
| Return type | `CachedSchema` | `CachedSchema` (same class) |
| Constructor params | `url`, `group_id`, `max_retries`, `retry_backoff_ms`, `retry_max_backoff_ms`, `http_client`, `auth` | identical |
| Cache safety | `threading.RLock` | `asyncio.Lock` |
| Cleanup | (automatic GC) | `async with` or `await client.aclose()` |
| Errors | `SchemaNotFoundError`, `RegistryConnectionError` | Same error types |

## Registering Schemas

`register_schema` posts a new schema artifact to the registry. The result is
cached so a subsequent `get_schema` call for the same `artifact_id` is always
a cache hit with no additional HTTP request:

```python
cached = await client.register_schema(
    "UserEvent",
    {
        "type": "record",
        "name": "UserEvent",
        "namespace": "com.example",
        "fields": [
            {"name": "userId", "type": "string"},
            {"name": "country", "type": "string"},
        ],
    },
    if_exists="FIND_OR_CREATE_VERSION",  # default — return existing or create new version
)
print(cached.global_id)   # Registry-assigned globalId
print(cached.content_id)  # Registry-assigned contentId
```

The `if_exists` parameter accepts `"FAIL"`, `"FIND_OR_CREATE_VERSION"`
(default), or `"CREATE_VERSION"`. `SchemaRegistrationError` is raised when
the registry returns a 4xx or 5xx response.

## Error Handling

The async client raises the same error types as the sync client:

```python
from apicurio_serdes._errors import (
    RegistryConnectionError,
    SchemaNotFoundError,
)

try:
    cached = await client.get_schema("NonExistent")
except SchemaNotFoundError as e:
    print(e.group_id)     # "my-group"
    print(e.artifact_id)  # "NonExistent"
except RegistryConnectionError as e:
    print(e.url)          # Registry URL that was unreachable
```

## Caching

Schemas are cached after the first fetch. Subsequent calls for the same
`artifact_id` return the cached result without contacting the registry.
Concurrent coroutines requesting the same uncached schema will result in
exactly one HTTP request (stampede prevention via `asyncio.Lock`).
