# Quickstart: Async Registry Client

**Feature**: 003-async-registry-client | **Date**: 2026-03-07

## Basic Async Schema Fetch

```python
import asyncio
from apicurio_serdes import AsyncApicurioRegistryClient

async def main():
    client = AsyncApicurioRegistryClient(
        url="http://registry:8080/apis/registry/v3",
        group_id="my-group",
    )
    try:
        cached = await client.get_schema("UserEvent")
        print(cached.schema)      # {"type": "record", "name": "UserEvent", ...}
        print(cached.global_id)   # 42
        print(cached.content_id)  # 7
    finally:
        await client.aclose()

asyncio.run(main())
```

## Using the Async Context Manager (Recommended)

```python
import asyncio
from apicurio_serdes import AsyncApicurioRegistryClient

async def main():
    async with AsyncApicurioRegistryClient(
        url="http://registry:8080/apis/registry/v3",
        group_id="my-group",
    ) as client:
        cached = await client.get_schema("UserEvent")
        print(cached.schema)

asyncio.run(main())
```

The context manager automatically calls `aclose()` on exit, even if an exception is raised.

## FastAPI Integration Example

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from apicurio_serdes import AsyncApicurioRegistryClient

registry_client: AsyncApicurioRegistryClient | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global registry_client
    registry_client = AsyncApicurioRegistryClient(
        url="http://registry:8080/apis/registry/v3",
        group_id="my-group",
    )
    yield
    await registry_client.aclose()

app = FastAPI(lifespan=lifespan)

@app.post("/produce")
async def produce(data: dict):
    cached = await registry_client.get_schema("UserEvent")
    # Use cached.schema for serialization ...
    return {"global_id": cached.global_id}
```

## Using Sync and Async Clients Side by Side

Both clients return the same `CachedSchema` type (SC-002, FR-003):

```python
from apicurio_serdes import ApicurioRegistryClient, AsyncApicurioRegistryClient
from apicurio_serdes._client import CachedSchema

# Sync client (for serializer/deserializer use)
sync_client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="my-group",
)
sync_schema: CachedSchema = sync_client.get_schema("UserEvent")

# Async client (for asyncio-based producers/consumers)
async with AsyncApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="my-group",
) as async_client:
    async_schema: CachedSchema = await async_client.get_schema("UserEvent")

# Both return identical CachedSchema instances for the same artifact
assert type(sync_schema) is type(async_schema)
```

## Test Scenarios

### Scenario: Basic schema retrieval

```python
import respx
import httpx
import pytest
from apicurio_serdes import AsyncApicurioRegistryClient

SCHEMA = {"type": "record", "name": "UserEvent", "fields": [{"name": "id", "type": "string"}]}

@pytest.fixture
def mock_registry():
    with respx.mock(base_url="http://registry:8080") as mock:
        mock.get(
            "/apis/registry/v3/groups/my-group/artifacts/UserEvent/versions/latest/content"
        ).mock(
            return_value=httpx.Response(
                200,
                json=SCHEMA,
                headers={"X-Registry-GlobalId": "42", "X-Registry-ContentId": "7"},
            )
        )
        yield mock

async def test_get_schema_returns_cached_schema(mock_registry):
    async with AsyncApicurioRegistryClient(
        url="http://registry:8080/apis/registry/v3",
        group_id="my-group",
    ) as client:
        result = await client.get_schema("UserEvent")

    assert result.schema == SCHEMA
    assert result.global_id == 42
    assert result.content_id == 7
```

### Scenario: Cache — registry contacted exactly once

```python
async def test_get_schema_caches_result(mock_registry):
    async with AsyncApicurioRegistryClient(
        url="http://registry:8080/apis/registry/v3",
        group_id="my-group",
    ) as client:
        first = await client.get_schema("UserEvent")
        second = await client.get_schema("UserEvent")

    assert first is second                          # same object
    assert mock_registry.calls.call_count == 1     # exactly one HTTP call (SC-003)
```

### Scenario: Not found → SchemaNotFoundError

```python
from apicurio_serdes._errors import SchemaNotFoundError

async def test_get_schema_raises_on_404():
    with respx.mock(base_url="http://registry:8080") as mock:
        mock.get(
            "/apis/registry/v3/groups/my-group/artifacts/Missing/versions/latest/content"
        ).mock(return_value=httpx.Response(404))

        async with AsyncApicurioRegistryClient(
            url="http://registry:8080/apis/registry/v3",
            group_id="my-group",
        ) as client:
            with pytest.raises(SchemaNotFoundError):
                await client.get_schema("Missing")
```
