"""Tests for AsyncApicurioRegistryClient."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx
from httpx import Response

from apicurio_serdes._async_client import AsyncApicurioRegistryClient
from tests.conftest import (
    CONTENT_ID,
    GLOBAL_ID,
    GROUP_ID,
    REGISTRY_URL,
    USER_EVENT_SCHEMA_JSON,
    _id_schema_route,
    _register_error_route,
    _register_route,
)


class TestConstructorValidation:
    """FR-008: Empty url or group_id raises ValueError."""

    def test_empty_url_raises_value_error(self) -> None:

        with pytest.raises(ValueError, match="url must not be empty"):
            AsyncApicurioRegistryClient(url="", group_id="my-group")

    def test_empty_group_id_raises_value_error(self) -> None:

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

        mock_registry.get(url__startswith=f"{REGISTRY_URL}/groups/").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
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

        route = _async_schema_route(mock_registry, "UserEvent")
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)

        result1 = await client.get_schema("UserEvent")
        result2 = await client.get_schema("UserEvent")

        assert route.call_count == 1
        assert result1 is result2

    async def test_different_artifacts_fetched_independently(
        self, mock_registry: respx.MockRouter
    ) -> None:

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


class TestLifecycleContextManager:
    """FR-009, FR-010: async with and explicit aclose()."""

    async def test_async_with_closes_http_client(self) -> None:

        async with AsyncApicurioRegistryClient(
            url=REGISTRY_URL, group_id=GROUP_ID
        ) as client:
            assert client._http_client.is_closed is False

        assert client._http_client.is_closed is True

    async def test_async_with_returns_self(self) -> None:

        instance = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        async with instance as client:
            assert client is instance
        await instance.aclose()

    async def test_async_with_closes_on_exception(self) -> None:

        with pytest.raises(RuntimeError, match="test error"):
            async with AsyncApicurioRegistryClient(
                url=REGISTRY_URL, group_id=GROUP_ID
            ) as client:
                raise RuntimeError("test error")

        assert client._http_client.is_closed is True

    async def test_explicit_aclose(self) -> None:

        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        assert client._http_client.is_closed is False
        await client.aclose()
        assert client._http_client.is_closed is True


class TestPackageExport:
    """FR-011: Top-level import of AsyncApicurioRegistryClient."""

    def test_import_from_top_level_package(self) -> None:
        from apicurio_serdes import AsyncApicurioRegistryClient
        from apicurio_serdes._async_client import (
            AsyncApicurioRegistryClient as DirectClass,
        )

        assert AsyncApicurioRegistryClient is DirectClass


class TestUnexpectedHttpStatus:
    """T019: Unexpected HTTP status (e.g. 500) raises RegistryConnectionError."""

    async def test_get_schema_500_raises_registry_connection_error(
        self, mock_registry: respx.MockRouter
    ) -> None:
        from apicurio_serdes._async_client import AsyncApicurioRegistryClient
        from apicurio_serdes._errors import RegistryConnectionError

        url = (
            f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/Broken/versions/latest/content"
        )
        mock_registry.get(url).mock(return_value=Response(500))
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)

        with pytest.raises(RegistryConnectionError):
            await client.get_schema("Broken")


class TestClosedClientGuard:
    """T021: get_schema on a closed client raises RuntimeError."""

    async def test_get_schema_after_aclose_raises(self) -> None:

        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        await client.aclose()

        with pytest.raises(RuntimeError):
            await client.get_schema("UserEvent")

    async def test_get_schema_after_async_with_raises(
        self, mock_registry: respx.MockRouter
    ) -> None:

        async with AsyncApicurioRegistryClient(
            url=REGISTRY_URL, group_id=GROUP_ID
        ) as client:
            pass

        with pytest.raises(RuntimeError):
            await client.get_schema("UserEvent")


class TestTransportErrors:
    """TD-001: TransportErrors beyond ConnectError raise RegistryConnectionError."""

    async def test_get_schema_read_timeout_raises_registry_connection_error(
        self, mock_registry: respx.MockRouter
    ) -> None:
        from apicurio_serdes._async_client import AsyncApicurioRegistryClient
        from apicurio_serdes._errors import RegistryConnectionError

        mock_registry.get(url__startswith=f"{REGISTRY_URL}/groups/").mock(
            side_effect=httpx.ReadTimeout("timed out")
        )
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        with pytest.raises(RegistryConnectionError):
            await client.get_schema("Slow")


class TestGetSchemaByGlobalId:
    """Async get_schema_by_global_id mirrors sync interface."""

    async def test_cache_miss_returns_schema(
        self, mock_registry: respx.MockRouter
    ) -> None:

        mock_registry.get(f"{REGISTRY_URL}/ids/globalIds/7").mock(
            return_value=httpx.Response(200, content=json.dumps(USER_EVENT_SCHEMA_JSON))
        )
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        result = await client.get_schema_by_global_id(7)
        assert result == USER_EVENT_SCHEMA_JSON

    async def test_cache_hit_no_second_request(
        self, mock_registry: respx.MockRouter
    ) -> None:

        route = mock_registry.get(f"{REGISTRY_URL}/ids/globalIds/7").mock(
            return_value=httpx.Response(200, content=json.dumps(USER_EVENT_SCHEMA_JSON))
        )
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        r1 = await client.get_schema_by_global_id(7)
        r2 = await client.get_schema_by_global_id(7)
        assert r1 == r2
        assert route.call_count == 1

    async def test_not_found_raises_schema_not_found_error(
        self, mock_registry: respx.MockRouter
    ) -> None:
        from apicurio_serdes._async_client import AsyncApicurioRegistryClient
        from apicurio_serdes._errors import SchemaNotFoundError

        mock_registry.get(f"{REGISTRY_URL}/ids/globalIds/999").mock(
            return_value=httpx.Response(404)
        )
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        with pytest.raises(SchemaNotFoundError) as exc_info:
            await client.get_schema_by_global_id(999)
        assert exc_info.value.id_type == "globalId"
        assert exc_info.value.id_value == 999

    async def test_network_error_raises_registry_connection_error(
        self, mock_registry: respx.MockRouter
    ) -> None:
        from apicurio_serdes._async_client import AsyncApicurioRegistryClient
        from apicurio_serdes._errors import RegistryConnectionError

        mock_registry.get(url__startswith=f"{REGISTRY_URL}/ids/globalIds/").mock(
            side_effect=httpx.ConnectError("refused")
        )
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        with pytest.raises(RegistryConnectionError):
            await client.get_schema_by_global_id(7)

    async def test_read_timeout_raises_registry_connection_error(
        self, mock_registry: respx.MockRouter
    ) -> None:
        from apicurio_serdes._async_client import AsyncApicurioRegistryClient
        from apicurio_serdes._errors import RegistryConnectionError

        mock_registry.get(url__startswith=f"{REGISTRY_URL}/ids/globalIds/").mock(
            side_effect=httpx.ReadTimeout("timed out")
        )
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        with pytest.raises(RegistryConnectionError):
            await client.get_schema_by_global_id(7)

    async def test_unexpected_status_raises_registry_connection_error(
        self, mock_registry: respx.MockRouter
    ) -> None:
        from apicurio_serdes._async_client import AsyncApicurioRegistryClient
        from apicurio_serdes._errors import RegistryConnectionError

        mock_registry.get(f"{REGISTRY_URL}/ids/globalIds/7").mock(
            return_value=httpx.Response(500)
        )
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        with pytest.raises(RegistryConnectionError):
            await client.get_schema_by_global_id(7)


class TestGetSchemaByContentId:
    """Async get_schema_by_content_id mirrors sync interface."""

    async def test_cache_miss_returns_schema(
        self, mock_registry: respx.MockRouter
    ) -> None:

        mock_registry.get(f"{REGISTRY_URL}/ids/contentIds/42").mock(
            return_value=httpx.Response(200, content=json.dumps(USER_EVENT_SCHEMA_JSON))
        )
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        result = await client.get_schema_by_content_id(42)
        assert result == USER_EVENT_SCHEMA_JSON

    async def test_cache_hit_no_second_request(
        self, mock_registry: respx.MockRouter
    ) -> None:

        route = mock_registry.get(f"{REGISTRY_URL}/ids/contentIds/42").mock(
            return_value=httpx.Response(200, content=json.dumps(USER_EVENT_SCHEMA_JSON))
        )
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        r1 = await client.get_schema_by_content_id(42)
        r2 = await client.get_schema_by_content_id(42)
        assert r1 == r2
        assert route.call_count == 1

    async def test_not_found_raises_schema_not_found_error(
        self, mock_registry: respx.MockRouter
    ) -> None:
        from apicurio_serdes._async_client import AsyncApicurioRegistryClient
        from apicurio_serdes._errors import SchemaNotFoundError

        mock_registry.get(f"{REGISTRY_URL}/ids/contentIds/9999").mock(
            return_value=httpx.Response(404)
        )
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        with pytest.raises(SchemaNotFoundError) as exc_info:
            await client.get_schema_by_content_id(9999)
        assert exc_info.value.id_type == "contentId"
        assert exc_info.value.id_value == 9999

    async def test_network_error_raises_registry_connection_error(
        self, mock_registry: respx.MockRouter
    ) -> None:
        from apicurio_serdes._async_client import AsyncApicurioRegistryClient
        from apicurio_serdes._errors import RegistryConnectionError

        mock_registry.get(url__startswith=f"{REGISTRY_URL}/ids/contentIds/").mock(
            side_effect=httpx.ConnectError("refused")
        )
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        with pytest.raises(RegistryConnectionError):
            await client.get_schema_by_content_id(42)


class TestInt64Validation:
    """Async client validates that globalId/contentId fit in signed 64-bit range."""

    async def test_global_id_outside_int64_raises_value_error(
        self, mock_registry: respx.MockRouter
    ) -> None:

        url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/OverflowTest/versions/latest/content"
        mock_registry.get(url).mock(
            return_value=Response(
                200,
                content=json.dumps(USER_EVENT_SCHEMA_JSON),
                headers={
                    "X-Registry-GlobalId": str(2**63),
                    "X-Registry-ContentId": "1",
                },
            )
        )
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        with pytest.raises(ValueError, match="globalId"):
            await client.get_schema("OverflowTest")

    async def test_content_id_outside_int64_raises_value_error(
        self, mock_registry: respx.MockRouter
    ) -> None:

        url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/OverflowTest2/versions/latest/content"
        mock_registry.get(url).mock(
            return_value=Response(
                200,
                content=json.dumps(USER_EVENT_SCHEMA_JSON),
                headers={
                    "X-Registry-GlobalId": "1",
                    "X-Registry-ContentId": str(2**63),
                },
            )
        )
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        with pytest.raises(ValueError, match="contentId"):
            await client.get_schema("OverflowTest2")


class TestClosedClientGuardIdMethods:
    """get_schema_by_X on a closed client raises RuntimeError."""

    async def test_get_schema_by_global_id_after_aclose_raises(self) -> None:

        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        await client.aclose()
        with pytest.raises(RuntimeError):
            await client.get_schema_by_global_id(7)


class TestIdCacheDoubleCheckLocking:
    """Coverage: inner cache-check return path for _id_cache."""

    async def test_inner_id_cache_check_returns_cached_value(self) -> None:
        from apicurio_serdes._base import _CacheCore

        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)

        cached_schema: dict[str, Any] = {"type": "record", "name": "X", "fields": []}
        cache_key = ("contentId", 42)
        get_count: dict[str, int] = {"n": 0}

        class _RaceCache(_CacheCore):
            def get(self, key: object) -> object:
                if key == cache_key:
                    get_count["n"] += 1
                    if get_count["n"] == 1:
                        super().set(cache_key, cached_schema)
                        return cached_schema
                return super().get(key)

        client._id_cache = _RaceCache(max_size=1000, ttl=None)  # type: ignore[assignment]
        result = await client.get_schema_by_content_id(42)
        assert result is cached_schema


class TestDoubleCheckLocking:
    """Coverage: exercise the inner cache-check return path."""

    async def test_inner_cache_check_returns_cached_value(self) -> None:
        from apicurio_serdes._async_client import AsyncApicurioRegistryClient
        from apicurio_serdes._base import _CacheCore
        from apicurio_serdes._client import CachedSchema

        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)

        pre_cached = CachedSchema(
            schema={"type": "record", "name": "X", "fields": []},
            global_id=99,
            content_id=88,
        )
        cache_key = (GROUP_ID, "Race")
        get_count: dict[str, int] = {"n": 0}

        class _RaceCache(_CacheCore):
            """_CacheCore whose get() simulates a concurrent fill on the first call."""

            def get(self, key: object) -> object:
                if key == cache_key:
                    get_count["n"] += 1
                    if get_count["n"] == 1:
                        super().set(cache_key, pre_cached)
                        return pre_cached
                return super().get(key)

        client._schema_cache = _RaceCache(max_size=1000, ttl=None)  # type: ignore[assignment]
        result = await client.get_schema("Race")
        assert result is pre_cached


# ── register_schema async tests ──


class TestRegisterSchemaAsync:
    """Async counterpart to sync register_schema tests."""

    async def test_happy_path(self, mock_registry: respx.MockRouter) -> None:
        """register_schema returns a CachedSchema with correct IDs."""
        from apicurio_serdes._base import CachedSchema

        _register_route(mock_registry, "UserEvent")
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        result = await client.register_schema("UserEvent", USER_EVENT_SCHEMA_JSON)
        assert isinstance(result, CachedSchema)
        assert result.schema == USER_EVENT_SCHEMA_JSON
        assert result.global_id == GLOBAL_ID
        assert result.content_id == CONTENT_ID

    async def test_populates_cache(self, mock_registry: respx.MockRouter) -> None:
        """After register_schema, get_schema is a cache hit."""
        _register_route(mock_registry, "UserEvent")
        get_route = _async_schema_route(mock_registry, "UserEvent")
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        await client.register_schema("UserEvent", USER_EVENT_SCHEMA_JSON)
        await client.get_schema("UserEvent")
        assert get_route.call_count == 0

    @pytest.mark.parametrize(
        "if_exists", ["FAIL", "CREATE_VERSION", "FIND_OR_CREATE_VERSION"]
    )
    async def test_forwards_if_exists(
        self, mock_registry: respx.MockRouter, if_exists: str
    ) -> None:
        """register_schema forwards if_exists as ifExists query param."""
        route = _register_route(mock_registry, "UserEvent", if_exists=if_exists)
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        await client.register_schema(
            "UserEvent", USER_EVENT_SCHEMA_JSON, if_exists=if_exists
        )
        assert route.call_count == 1

    async def test_default_if_exists_is_find_or_create_version(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """Default if_exists is 'FIND_OR_CREATE_VERSION'."""
        route = _register_route(
            mock_registry, "UserEvent", if_exists="FIND_OR_CREATE_VERSION"
        )
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        await client.register_schema("UserEvent", USER_EVENT_SCHEMA_JSON)
        assert route.call_count == 1

    async def test_409_raises_schema_registration_error(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """409 raises SchemaRegistrationError with artifact_id."""
        from apicurio_serdes._errors import SchemaRegistrationError

        _register_error_route(mock_registry, 409)
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        with pytest.raises(SchemaRegistrationError) as exc_info:
            await client.register_schema("UserEvent", USER_EVENT_SCHEMA_JSON)
        assert exc_info.value.artifact_id == "UserEvent"

    async def test_500_raises_schema_registration_error(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """500 raises SchemaRegistrationError."""
        from apicurio_serdes._errors import SchemaRegistrationError

        _register_error_route(mock_registry, 500)
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        with pytest.raises(SchemaRegistrationError):
            await client.register_schema("UserEvent", USER_EVENT_SCHEMA_JSON)

    async def test_network_error_raises_registry_connection_error(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """Network failure raises RegistryConnectionError."""
        from apicurio_serdes._errors import RegistryConnectionError

        mock_registry.post(
            url__startswith=f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts"
        ).mock(side_effect=httpx.ConnectError("refused"))
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        with pytest.raises(RegistryConnectionError):
            await client.register_schema("UserEvent", USER_EVENT_SCHEMA_JSON)

    async def test_closed_client_raises_runtime_error(self) -> None:
        """register_schema on a closed client raises RuntimeError."""
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        await client.aclose()
        with pytest.raises(RuntimeError, match="closed"):
            await client.register_schema("UserEvent", USER_EVENT_SCHEMA_JSON)

    async def test_missing_version_key_raises_schema_registration_error(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """200 response missing version.globalId in body raises SchemaRegistrationError."""
        from httpx import Response

        from apicurio_serdes._errors import SchemaRegistrationError

        url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts"
        mock_registry.post(url).mock(
            return_value=Response(
                200,
                json={"artifact": {}, "version": {"contentId": 1}},
                # globalId intentionally omitted from version
            )
        )
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        with pytest.raises(SchemaRegistrationError):
            await client.register_schema("UserEvent", USER_EVENT_SCHEMA_JSON)

    async def test_fast_path_cache_hit(self) -> None:
        """Pre-populated cache means register_schema never POSTs."""
        from apicurio_serdes._base import CachedSchema

        cached = CachedSchema(
            schema=USER_EVENT_SCHEMA_JSON, global_id=99, content_id=88
        )
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        client._schema_cache.set((GROUP_ID, "UserEvent"), cached)
        result = await client.register_schema("UserEvent", USER_EVENT_SCHEMA_JSON)
        assert result is cached

    async def test_double_check_locking(self) -> None:
        """Exercise the inner double-check path for async register_schema."""
        from apicurio_serdes._base import CachedSchema, _CacheCore

        pre_cached = CachedSchema(
            schema=USER_EVENT_SCHEMA_JSON, global_id=99, content_id=88
        )
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)

        cache_key = (GROUP_ID, "UserEvent")
        get_count: dict[str, int] = {"n": 0}

        class _RaceCache(_CacheCore):
            def get(self, key: object) -> object:
                if key == cache_key:
                    get_count["n"] += 1
                    if get_count["n"] == 1:
                        super().set(cache_key, pre_cached)
                        return pre_cached
                return super().get(key)

        client._schema_cache = _RaceCache(max_size=1000, ttl=None)  # type: ignore[assignment]
        result = await client.register_schema("UserEvent", USER_EVENT_SCHEMA_JSON)
        assert result is pre_cached

    def test_interface_parity_with_sync_client(self) -> None:
        """register_schema signature matches the sync client."""
        import inspect

        from apicurio_serdes._client import ApicurioRegistryClient

        sync_sig = inspect.signature(ApicurioRegistryClient.register_schema)
        async_sig = inspect.signature(AsyncApicurioRegistryClient.register_schema)
        assert list(sync_sig.parameters) == list(async_sig.parameters)
        for name in sync_sig.parameters:
            if name == "self":
                continue
            assert (
                sync_sig.parameters[name].default == async_sig.parameters[name].default
            ), f"Default mismatch for param '{name}'"


# ── Auth wiring tests ──


def test_async_client_auth_defaults_to_none() -> None:
    """auth parameter defaults to None; existing tests unaffected."""
    import inspect

    params = inspect.signature(AsyncApicurioRegistryClient.__init__).parameters
    assert "auth" in params
    assert params["auth"].default is None


@pytest.mark.asyncio
async def test_async_client_accepts_bearer_auth(
    mock_registry: respx.MockRouter,
) -> None:
    """AsyncApicurioRegistryClient accepts auth=BearerAuth and passes it to httpx."""
    from httpx import Response

    from apicurio_serdes._auth import BearerAuth

    url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/Auth/versions/latest/content"
    route = mock_registry.get(url).mock(
        return_value=Response(
            200,
            content=b'{"type":"record","name":"X","fields":[]}',
            headers={"X-Registry-GlobalId": "1", "X-Registry-ContentId": "2"},
        )
    )
    client = AsyncApicurioRegistryClient(
        url=REGISTRY_URL, group_id=GROUP_ID, auth=BearerAuth(token="async-wire")
    )
    await client.get_schema("Auth")
    assert route.calls[0].request.headers["authorization"] == "Bearer async-wire"


# ── Retry and escape hatch tests (#37) ──


def _async_flaky_schema_handler(n_failures: int) -> Any:
    """Side-effect: raises ConnectError n_failures times, then returns 200."""
    count = 0

    def _handler(request: httpx.Request) -> httpx.Response:
        nonlocal count
        count += 1
        if count <= n_failures:
            raise httpx.ConnectError("transient failure")
        return httpx.Response(
            200,
            content=json.dumps(USER_EVENT_SCHEMA_JSON).encode(),
            headers={
                "X-Registry-GlobalId": str(GLOBAL_ID),
                "X-Registry-ContentId": str(CONTENT_ID),
            },
        )

    return _handler


def _async_flaky_status_schema_handler(fail_status: int, n_failures: int) -> Any:
    """Side-effect: returns fail_status n_failures times, then returns 200."""
    count = 0

    def _handler(request: httpx.Request) -> httpx.Response:
        nonlocal count
        count += 1
        if count <= n_failures:
            return httpx.Response(fail_status)
        return httpx.Response(
            200,
            content=json.dumps(USER_EVENT_SCHEMA_JSON).encode(),
            headers={
                "X-Registry-GlobalId": str(GLOBAL_ID),
                "X-Registry-ContentId": str(CONTENT_ID),
            },
        )

    return _handler


def _async_flaky_id_handler(n_failures: int) -> Any:
    """Side-effect: ConnectError n times then valid schema response (ID endpoint)."""
    count = 0

    def _handler(request: httpx.Request) -> httpx.Response:
        nonlocal count
        count += 1
        if count <= n_failures:
            raise httpx.ConnectError("transient failure")
        return httpx.Response(200, content=json.dumps(USER_EVENT_SCHEMA_JSON).encode())

    return _handler


def _async_flaky_register_handler(n_failures: int) -> Any:
    """Side-effect: ConnectError n times then valid register response."""
    count = 0

    def _handler(request: httpx.Request) -> httpx.Response:
        nonlocal count
        count += 1
        if count <= n_failures:
            raise httpx.ConnectError("transient failure")
        return httpx.Response(
            200,
            json={
                "artifact": {
                    "groupId": GROUP_ID,
                    "artifactId": "UserEvent",
                    "artifactType": "AVRO",
                },
                "version": {
                    "globalId": GLOBAL_ID,
                    "contentId": CONTENT_ID,
                    "artifactType": "AVRO",
                },
            },
        )

    return _handler


# Constructor parameter tests


def test_async_init_default_max_retries() -> None:
    """Default max_retries is 3."""
    client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    assert client.max_retries == 3


def test_async_init_default_retry_backoff_ms() -> None:
    """Default retry_backoff_ms is 1000."""
    client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    assert client.retry_backoff_ms == 1000


def test_async_init_default_retry_max_backoff_ms() -> None:
    """Default retry_max_backoff_ms is 20000."""
    client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    assert client.retry_max_backoff_ms == 20000


def test_async_init_max_retries_zero_valid() -> None:
    """max_retries=0 is valid."""
    client = AsyncApicurioRegistryClient(
        url=REGISTRY_URL, group_id=GROUP_ID, max_retries=0
    )
    assert client.max_retries == 0


def test_async_init_max_retries_negative_raises_value_error() -> None:
    """max_retries=-1 raises ValueError."""
    with pytest.raises(ValueError, match="max_retries"):
        AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID, max_retries=-1)


def test_async_init_signature_matches_sync() -> None:
    """Async and sync client __init__ have the same parameter names."""
    import inspect

    from apicurio_serdes import ApicurioRegistryClient

    sync_params = set(inspect.signature(ApicurioRegistryClient.__init__).parameters) - {
        "self"
    }
    async_params = set(
        inspect.signature(AsyncApicurioRegistryClient.__init__).parameters
    ) - {"self"}
    assert sync_params == async_params


# Retry on transport error


async def test_async_get_schema_retries_on_connect_error_then_succeeds(
    mock_registry: respx.MockRouter,
) -> None:
    """ConnectError on first attempt retried; schema returned on second attempt."""
    url = (
        f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/UserEvent/versions/latest/content"
    )
    mock_registry.get(url).mock(side_effect=_async_flaky_schema_handler(1))
    client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with patch("apicurio_serdes._async_client.asyncio.sleep", new_callable=AsyncMock):
        result = await client.get_schema("UserEvent")
    assert result.schema == USER_EVENT_SCHEMA_JSON


async def test_async_get_schema_exhausts_retries_raises_connection_error(
    mock_registry: respx.MockRouter,
) -> None:
    """All attempts fail; RegistryConnectionError raised after max_retries exhausted."""
    from apicurio_serdes._errors import RegistryConnectionError

    url = (
        f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/UserEvent/versions/latest/content"
    )
    route = mock_registry.get(url).mock(side_effect=_async_flaky_schema_handler(99))
    client = AsyncApicurioRegistryClient(
        url=REGISTRY_URL, group_id=GROUP_ID, max_retries=2
    )
    with (
        patch("apicurio_serdes._async_client.asyncio.sleep", new_callable=AsyncMock),
        pytest.raises(RegistryConnectionError),
    ):
        await client.get_schema("UserEvent")
    assert route.call_count == 3


async def test_async_get_schema_by_global_id_retries_on_connect_error(
    mock_registry: respx.MockRouter,
) -> None:
    """ID lookup retried on ConnectError."""
    mock_registry.get(url__startswith=f"{REGISTRY_URL}/ids/globalIds/").mock(
        side_effect=_async_flaky_id_handler(1)
    )
    client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with patch("apicurio_serdes._async_client.asyncio.sleep", new_callable=AsyncMock):
        result = await client.get_schema_by_global_id(GLOBAL_ID)
    assert result == USER_EVENT_SCHEMA_JSON


async def test_async_register_schema_retries_on_connect_error(
    mock_registry: respx.MockRouter,
) -> None:
    """register_schema retried on ConnectError."""
    mock_registry.post(url__startswith=f"{REGISTRY_URL}/groups/").mock(
        side_effect=_async_flaky_register_handler(1)
    )
    client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with patch("apicurio_serdes._async_client.asyncio.sleep", new_callable=AsyncMock):
        result = await client.register_schema("UserEvent", USER_EVENT_SCHEMA_JSON)
    assert result.global_id == GLOBAL_ID


# Retry on retryable HTTP status codes


@pytest.mark.parametrize("fail_status", [429, 502, 503, 504])
async def test_async_get_schema_retries_on_retryable_status(
    mock_registry: respx.MockRouter, fail_status: int
) -> None:
    """Schema GET retried on 429/502/503/504."""
    url = (
        f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/UserEvent/versions/latest/content"
    )
    mock_registry.get(url).mock(
        side_effect=_async_flaky_status_schema_handler(fail_status, 1)
    )
    client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with patch("apicurio_serdes._async_client.asyncio.sleep", new_callable=AsyncMock):
        result = await client.get_schema("UserEvent")
    assert result.schema == USER_EVENT_SCHEMA_JSON


# No retry on non-retryable errors


async def test_async_get_schema_no_retry_on_404(
    mock_registry: respx.MockRouter,
) -> None:
    """404 raises SchemaNotFoundError immediately — no retry."""
    from apicurio_serdes._errors import SchemaNotFoundError

    url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/Missing/versions/latest/content"
    route = mock_registry.get(url).mock(return_value=httpx.Response(404, json={}))
    client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(SchemaNotFoundError):
        await client.get_schema("Missing")
    assert route.call_count == 1


async def test_async_get_schema_no_retry_on_400(
    mock_registry: respx.MockRouter,
) -> None:
    """400 raises RegistryConnectionError immediately — no retry."""
    from apicurio_serdes._errors import RegistryConnectionError

    url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/Bad/versions/latest/content"
    route = mock_registry.get(url).mock(return_value=httpx.Response(400))
    client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(RegistryConnectionError):
        await client.get_schema("Bad")
    assert route.call_count == 1


async def test_async_get_schema_no_retry_on_500(
    mock_registry: respx.MockRouter,
) -> None:
    """500 raises RegistryConnectionError immediately — not retried."""
    from apicurio_serdes._errors import RegistryConnectionError

    url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/Broken/versions/latest/content"
    route = mock_registry.get(url).mock(return_value=httpx.Response(500))
    client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(RegistryConnectionError):
        await client.get_schema("Broken")
    assert route.call_count == 1


async def test_async_get_schema_max_retries_zero_no_retry(
    mock_registry: respx.MockRouter,
) -> None:
    """max_retries=0 disables retry; ConnectError raises after 1 attempt."""
    from apicurio_serdes._errors import RegistryConnectionError

    url = (
        f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/UserEvent/versions/latest/content"
    )
    route = mock_registry.get(url).mock(side_effect=httpx.ConnectError("refused"))
    client = AsyncApicurioRegistryClient(
        url=REGISTRY_URL, group_id=GROUP_ID, max_retries=0
    )
    with pytest.raises(RegistryConnectionError):
        await client.get_schema("UserEvent")
    assert route.call_count == 1


async def test_async_get_schema_exhausts_retries_on_503_raises_connection_error(
    mock_registry: respx.MockRouter,
) -> None:
    """When all retries on 503 are exhausted, RegistryConnectionError is raised."""
    from apicurio_serdes._errors import RegistryConnectionError

    url = (
        f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/UserEvent/versions/latest/content"
    )
    mock_registry.get(url).mock(return_value=httpx.Response(503))
    client = AsyncApicurioRegistryClient(
        url=REGISTRY_URL, group_id=GROUP_ID, max_retries=1
    )
    with (
        patch("apicurio_serdes._async_client.asyncio.sleep", new_callable=AsyncMock),
        pytest.raises(RegistryConnectionError),
    ):
        await client.get_schema("UserEvent")


# Backoff


async def test_async_get_schema_sleep_called_between_retries(
    mock_registry: respx.MockRouter,
) -> None:
    """asyncio.sleep is called with a non-negative delay between retry attempts."""
    url = (
        f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/UserEvent/versions/latest/content"
    )
    mock_registry.get(url).mock(side_effect=_async_flaky_schema_handler(1))
    client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with patch(
        "apicurio_serdes._async_client.asyncio.sleep", new_callable=AsyncMock
    ) as mock_sleep:
        await client.get_schema("UserEvent")
    mock_sleep.assert_called_once()
    delay = mock_sleep.call_args[0][0]
    assert delay >= 0


# Escape hatch: custom http_client


async def test_async_custom_http_client_is_used() -> None:
    """User-provided AsyncClient is used for HTTP requests."""
    mock_client = MagicMock(spec=httpx.AsyncClient)
    _req = httpx.Request(
        "GET",
        f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/UserEvent/versions/latest/content",
    )
    mock_client.request = AsyncMock(
        return_value=httpx.Response(
            200,
            content=json.dumps(USER_EVENT_SCHEMA_JSON).encode(),
            headers={
                "X-Registry-GlobalId": str(GLOBAL_ID),
                "X-Registry-ContentId": str(CONTENT_ID),
            },
            request=_req,
        )
    )
    client = AsyncApicurioRegistryClient(
        url=REGISTRY_URL, group_id=GROUP_ID, http_client=mock_client
    )
    result = await client.get_schema("UserEvent")
    assert result.schema == USER_EVENT_SCHEMA_JSON
    assert mock_client.request.called


async def test_async_custom_http_client_not_closed_on_aclose() -> None:
    """User-provided AsyncClient is not closed when aclose() is called."""
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_client.aclose = AsyncMock()
    client = AsyncApicurioRegistryClient(
        url=REGISTRY_URL, group_id=GROUP_ID, http_client=mock_client
    )
    await client.aclose()
    mock_client.aclose.assert_not_called()


# ── Async cache constructor validation tests ──


class TestAsyncCacheConstructorValidation:
    """cache_max_size and cache_ttl_seconds are validated on construction (async client)."""

    def test_cache_max_size_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="cache_max_size"):
            AsyncApicurioRegistryClient(
                url=REGISTRY_URL, group_id=GROUP_ID, cache_max_size=0
            )

    def test_cache_max_size_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="cache_max_size"):
            AsyncApicurioRegistryClient(
                url=REGISTRY_URL, group_id=GROUP_ID, cache_max_size=-1
            )

    def test_cache_ttl_seconds_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="cache_ttl_seconds"):
            AsyncApicurioRegistryClient(
                url=REGISTRY_URL, group_id=GROUP_ID, cache_ttl_seconds=0
            )

    def test_cache_ttl_seconds_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="cache_ttl_seconds"):
            AsyncApicurioRegistryClient(
                url=REGISTRY_URL, group_id=GROUP_ID, cache_ttl_seconds=-1.0
            )

    def test_valid_cache_params_constructs_without_error(self) -> None:
        client = AsyncApicurioRegistryClient(
            url=REGISTRY_URL,
            group_id=GROUP_ID,
            cache_max_size=1,
            cache_ttl_seconds=30.0,
        )
        assert client is not None

    def test_default_cache_max_size_is_1000(self) -> None:
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        assert client._schema_cache._max_size == 1000
        assert client._id_cache._max_size == 1000

    def test_default_cache_ttl_seconds_is_none(self) -> None:
        client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
        assert client._schema_cache._ttl is None
        assert client._id_cache._ttl is None

    def test_id_cache_always_has_no_ttl(self) -> None:
        """_id_cache always constructed with ttl=None regardless of cache_ttl_seconds."""
        client = AsyncApicurioRegistryClient(
            url=REGISTRY_URL, group_id=GROUP_ID, cache_ttl_seconds=60.0
        )
        assert client._id_cache._ttl is None
        assert client._schema_cache._ttl == 60.0


# ── Async LRU eviction tests ──


class TestAsyncClientLRUEviction:
    """cache_max_size causes LRU eviction in the async schema cache."""

    async def test_lru_eviction_in_schema_cache(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """With cache_max_size=2, fetching 3 schemas evicts the LRU (first) entry."""
        schema_a: dict[str, Any] = {"type": "record", "name": "A", "fields": []}
        schema_b: dict[str, Any] = {"type": "record", "name": "B", "fields": []}
        schema_c: dict[str, Any] = {"type": "record", "name": "C", "fields": []}
        route_a = _async_schema_route(
            mock_registry, "A", schema=schema_a, global_id=1, content_id=1
        )
        route_b = _async_schema_route(
            mock_registry, "B", schema=schema_b, global_id=2, content_id=2
        )
        _async_schema_route(
            mock_registry, "C", schema=schema_c, global_id=3, content_id=3
        )

        client = AsyncApicurioRegistryClient(
            url=REGISTRY_URL, group_id=GROUP_ID, cache_max_size=2
        )
        await client.get_schema("A")  # cache: [A]
        await client.get_schema("B")  # cache: [A, B]
        await client.get_schema("C")  # evicts A → cache: [B, C]

        assert route_a.call_count == 1
        assert route_b.call_count == 1

        # Re-fetch A — was evicted; evicts B → cache: [C, A]
        await client.get_schema("A")
        assert route_a.call_count == 2

        # B was evicted when A was re-inserted — must re-fetch
        await client.get_schema("B")
        assert route_b.call_count == 2


# ── Async TTL expiry tests ──


class TestAsyncClientTTLExpiry:
    """cache_ttl_seconds causes TTL expiry in the async schema cache only."""

    async def test_schema_cache_hit_before_ttl(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """get_schema is a cache hit before TTL elapses."""
        route = _async_schema_route(mock_registry, "UserEvent")
        client = AsyncApicurioRegistryClient(
            url=REGISTRY_URL, group_id=GROUP_ID, cache_ttl_seconds=60.0
        )
        with patch("apicurio_serdes._base.time") as mock_time:
            mock_time.monotonic.return_value = 100.0
            await client.get_schema("UserEvent")
            mock_time.monotonic.return_value = 155.0  # within TTL
            await client.get_schema("UserEvent")
        assert route.call_count == 1

    async def test_schema_cache_miss_after_ttl(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """get_schema re-fetches from registry after TTL elapses."""
        route = _async_schema_route(mock_registry, "UserEvent")
        client = AsyncApicurioRegistryClient(
            url=REGISTRY_URL, group_id=GROUP_ID, cache_ttl_seconds=60.0
        )
        with patch("apicurio_serdes._base.time") as mock_time:
            mock_time.monotonic.return_value = 100.0
            await client.get_schema("UserEvent")
            # Advance past TTL (expiry = 160.0)
            mock_time.monotonic.return_value = 160.0
            await client.get_schema("UserEvent")
        assert route.call_count == 2

    async def test_id_cache_not_expired_after_ttl(
        self, mock_registry: respx.MockRouter
    ) -> None:
        """ID-based lookups are never expired even when cache_ttl_seconds is set."""
        route = _id_schema_route(mock_registry, "globalId", GLOBAL_ID)
        client = AsyncApicurioRegistryClient(
            url=REGISTRY_URL, group_id=GROUP_ID, cache_ttl_seconds=60.0
        )
        with patch("apicurio_serdes._base.time") as mock_time:
            mock_time.monotonic.return_value = 100.0
            await client.get_schema_by_global_id(GLOBAL_ID)
            # Advance well past TTL
            mock_time.monotonic.return_value = 9999.0
            await client.get_schema_by_global_id(GLOBAL_ID)
        # Still only 1 HTTP call — ID cache never expired
        assert route.call_count == 1
