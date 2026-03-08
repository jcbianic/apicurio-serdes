"""Tests for AsyncApicurioRegistryClient."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx
from httpx import Response

from tests.conftest import (
    CONTENT_ID,
    GLOBAL_ID,
    GROUP_ID,
    REGISTRY_URL,
    USER_EVENT_SCHEMA_JSON,
)


class TestConstructorValidation:
    """FR-008: Empty url or group_id raises ValueError."""

    def test_empty_url_raises_value_error(self) -> None:
        from apicurio_serdes._async_client import AsyncApicurioRegistryClient

        with pytest.raises(ValueError, match="url must not be empty"):
            AsyncApicurioRegistryClient(url="", group_id="my-group")

    def test_empty_group_id_raises_value_error(self) -> None:
        from apicurio_serdes._async_client import AsyncApicurioRegistryClient

        with pytest.raises(ValueError, match="group_id must not be empty"):
            AsyncApicurioRegistryClient(
                url="http://registry:8080/apis/registry/v3", group_id=""
            )


def _async_schema_route(
    router: respx.MockRouter,
    artifact_id: str,
    *,
    group_id: str = GROUP_ID,
    schema: dict[str, Any] = USER_EVENT_SCHEMA_JSON,
    global_id: int = GLOBAL_ID,
    content_id: int = CONTENT_ID,
) -> respx.Route:
    """Register a mock route returning a schema for the async client."""
    url = f"{REGISTRY_URL}/groups/{group_id}/artifacts/{artifact_id}/versions/latest/content"
    return router.get(url).mock(
        return_value=Response(
            200,
            content=json.dumps(schema),
            headers={
                "X-Registry-GlobalId": str(global_id),
                "X-Registry-ContentId": str(content_id),
            },
        )
    )


def _async_not_found_route(
    router: respx.MockRouter,
    artifact_id: str,
    *,
    group_id: str = GROUP_ID,
) -> respx.Route:
    """Register a mock route returning 404 for the async client."""
    url = f"{REGISTRY_URL}/groups/{group_id}/artifacts/{artifact_id}/versions/latest/content"
    return router.get(url).mock(return_value=Response(404))


class TestGetSchemaSuccess:
    """FR-001, FR-002, SC-001: Successful async schema retrieval."""

    async def test_get_schema_returns_cached_schema(
        self, mock_registry: respx.MockRouter
    ) -> None:
        from apicurio_serdes._async_client import AsyncApicurioRegistryClient
        from apicurio_serdes._client import CachedSchema

        _async_schema_route(mock_registry, "UserEvent")
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)

        result = await client.get_schema("UserEvent")

        assert isinstance(result, CachedSchema)
        assert result.schema == USER_EVENT_SCHEMA_JSON
        assert result.global_id == GLOBAL_ID
        assert result.content_id == CONTENT_ID


class TestSchemaNotFoundError:
    """FR-005: HTTP 404 raises SchemaNotFoundError."""

    async def test_get_schema_404_raises_schema_not_found(
        self, mock_registry: respx.MockRouter
    ) -> None:
        from apicurio_serdes._async_client import AsyncApicurioRegistryClient
        from apicurio_serdes._errors import SchemaNotFoundError

        _async_not_found_route(mock_registry, "NonExistent")
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)

        with pytest.raises(SchemaNotFoundError) as exc_info:
            await client.get_schema("NonExistent")

        assert exc_info.value.group_id == GROUP_ID
        assert exc_info.value.artifact_id == "NonExistent"


class TestRegistryConnectionError:
    """FR-006: Network error raises RegistryConnectionError."""

    async def test_get_schema_connect_error_raises_registry_connection_error(
        self, mock_registry: respx.MockRouter
    ) -> None:
        from apicurio_serdes._async_client import AsyncApicurioRegistryClient
        from apicurio_serdes._errors import RegistryConnectionError

        mock_registry.get(
            url__startswith=f"{REGISTRY_URL}/groups/"
        ).mock(side_effect=httpx.ConnectError("Connection refused"))
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)

        with pytest.raises(RegistryConnectionError) as exc_info:
            await client.get_schema("UserEvent")

        assert exc_info.value.url == REGISTRY_URL


SCHEMA_B_JSON: dict[str, Any] = {
    "type": "record",
    "name": "SchemaB",
    "namespace": "com.example",
    "fields": [{"name": "id", "type": "string"}],
}


class TestSchemaCaching:
    """FR-004, SC-003: Cache prevents redundant HTTP calls."""

    async def test_same_artifact_called_twice_contacts_registry_once(
        self, mock_registry: respx.MockRouter
    ) -> None:
        from apicurio_serdes._async_client import AsyncApicurioRegistryClient

        route = _async_schema_route(mock_registry, "UserEvent")
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)

        result1 = await client.get_schema("UserEvent")
        result2 = await client.get_schema("UserEvent")

        assert route.call_count == 1
        assert result1 is result2

    async def test_different_artifacts_fetched_independently(
        self, mock_registry: respx.MockRouter
    ) -> None:
        from apicurio_serdes._async_client import AsyncApicurioRegistryClient

        route_a = _async_schema_route(
            mock_registry, "SchemaA", global_id=10, content_id=1
        )
        route_b = _async_schema_route(
            mock_registry, "SchemaB", schema=SCHEMA_B_JSON, global_id=20, content_id=2
        )
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)

        result_a = await client.get_schema("SchemaA")
        result_b = await client.get_schema("SchemaB")

        assert route_a.call_count == 1
        assert route_b.call_count == 1
        assert result_a.schema == USER_EVENT_SCHEMA_JSON
        assert result_b.schema == SCHEMA_B_JSON


class TestConcurrentStampedePrevention:
    """NFR-001: Concurrent coroutines for same artifact → exactly 1 HTTP request."""

    async def test_concurrent_get_schema_single_http_request(
        self, mock_registry: respx.MockRouter
    ) -> None:
        import asyncio

        from apicurio_serdes._async_client import AsyncApicurioRegistryClient

        route = _async_schema_route(mock_registry, "UserEvent")
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)

        results = await asyncio.gather(
            *[client.get_schema("UserEvent") for _ in range(10)]
        )

        assert route.call_count == 1
        assert all(r is results[0] for r in results)


class TestInterfaceParity:
    """FR-003, SC-002, SC-004: Async client mirrors sync client interface."""

    def test_constructor_accepts_same_parameters(self) -> None:
        import inspect

        from apicurio_serdes._async_client import AsyncApicurioRegistryClient
        from apicurio_serdes._client import ApicurioRegistryClient

        sync_params = list(
            inspect.signature(ApicurioRegistryClient.__init__).parameters.keys()
        )
        async_params = list(
            inspect.signature(AsyncApicurioRegistryClient.__init__).parameters.keys()
        )
        assert sync_params == async_params

    async def test_get_schema_returns_same_cached_schema_type(
        self, mock_registry: respx.MockRouter
    ) -> None:
        from apicurio_serdes._async_client import AsyncApicurioRegistryClient
        from apicurio_serdes._client import CachedSchema

        _async_schema_route(mock_registry, "UserEvent")
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)

        result = await client.get_schema("UserEvent")

        assert type(result) is CachedSchema
