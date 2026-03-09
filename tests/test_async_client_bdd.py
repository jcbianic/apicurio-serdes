"""BDD step definitions for 003-async-registry-client feature files."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
import pytest
import respx
from httpx import Response
from pytest_bdd import given, parsers, scenario, then, when

from apicurio_serdes._async_client import AsyncApicurioRegistryClient
from apicurio_serdes._client import CachedSchema
from apicurio_serdes._errors import RegistryConnectionError, SchemaNotFoundError
from tests.conftest import (
    CONTENT_ID,
    GLOBAL_ID,
    GROUP_ID,
    REGISTRY_URL,
    USER_EVENT_SCHEMA_JSON,
)

FEATURE_DIR = "../specs/003-async-registry-client/tests/features"

# ═══════════════════════════════════════════════════════════════
# schema_retrieval.feature — US-001
# ═══════════════════════════════════════════════════════════════


@scenario(
    f"{FEATURE_DIR}/schema_retrieval.feature",
    "Successful async schema retrieval returns CachedSchema",
)
def test_ts001_successful_retrieval() -> None:
    """TS-001."""


@scenario(
    f"{FEATURE_DIR}/schema_retrieval.feature",
    "Artifact not found raises SchemaNotFoundError",
)
def test_ts002_not_found() -> None:
    """TS-002."""


@scenario(
    f"{FEATURE_DIR}/schema_retrieval.feature",
    "Registry unreachable raises RegistryConnectionError",
)
def test_ts003_unreachable() -> None:
    """TS-003."""


@scenario(
    f"{FEATURE_DIR}/schema_retrieval.feature",
    "group_id is applied to every schema lookup",
)
def test_ts004_group_id_applied() -> None:
    """TS-004."""


@scenario(
    f"{FEATURE_DIR}/schema_retrieval.feature",
    "get_schema returns the shared CachedSchema type",
)
def test_ts005_shared_type() -> None:
    """TS-005."""


# ═══════════════════════════════════════════════════════════════
# schema_caching.feature — US-002
# ═══════════════════════════════════════════════════════════════


@scenario(
    f"{FEATURE_DIR}/schema_caching.feature",
    "Same artifact fetched twice contacts the registry exactly once",
)
def test_ts011_cache_single() -> None:
    """TS-011."""


@scenario(
    f"{FEATURE_DIR}/schema_caching.feature",
    "Fetching a different artifact does not re-fetch a cached schema",
)
def test_ts012_cache_different() -> None:
    """TS-012."""


@scenario(
    f"{FEATURE_DIR}/schema_caching.feature",
    "Concurrent coroutines fetching the same uncached schema result in one HTTP request",
)
def test_ts013_stampede() -> None:
    """TS-013."""


# ═══════════════════════════════════════════════════════════════
# interface_compatibility.feature — US-003
# ═══════════════════════════════════════════════════════════════


@scenario(
    f"{FEATURE_DIR}/interface_compatibility.feature",
    "AsyncApicurioRegistryClient accepts the same constructor parameters as the sync client",
)
def test_ts021_same_params() -> None:
    """TS-021."""


@scenario(
    f"{FEATURE_DIR}/interface_compatibility.feature",
    "get_schema is the method name on the async client",
)
def test_ts022_method_name() -> None:
    """TS-022."""


@scenario(
    f"{FEATURE_DIR}/interface_compatibility.feature",
    "Async client raises the same error types as the sync client",
)
def test_ts023_same_errors() -> None:
    """TS-023."""


@scenario(
    f"{FEATURE_DIR}/interface_compatibility.feature",
    "AsyncApicurioRegistryClient is importable from the top-level package",
)
def test_ts024_importable() -> None:
    """TS-024."""


# ═══════════════════════════════════════════════════════════════
# lifecycle_management.feature — US-004
# ═══════════════════════════════════════════════════════════════


@scenario(
    f"{FEATURE_DIR}/lifecycle_management.feature",
    "async with block closes the HTTP connection pool on exit",
)
def test_ts031_context_manager_close() -> None:
    """TS-031."""


@scenario(
    f"{FEATURE_DIR}/lifecycle_management.feature",
    "async with block closes the HTTP connection pool when an exception is raised",
)
def test_ts032_context_manager_exception() -> None:
    """TS-032."""


@scenario(
    f"{FEATURE_DIR}/lifecycle_management.feature",
    "aclose() closes the HTTP connection pool explicitly",
)
def test_ts033_explicit_aclose() -> None:
    """TS-033."""


# ═══════════════════════════════════════════════════════════════
# validation.feature
# ═══════════════════════════════════════════════════════════════


@scenario(
    f"{FEATURE_DIR}/validation.feature", "Empty constructor parameters raise ValueError"
)
def test_ts041_validation() -> None:
    """TS-041."""


# ═══════════════════════════════════════════════════════════════
# Shared Background step
# ═══════════════════════════════════════════════════════════════


@given(
    "a configured AsyncApicurioRegistryClient pointing at a stubbed registry",
    target_fixture="async_client_and_registry",
)
def given_async_client_with_stubbed_registry(
    mock_registry: respx.MockRouter,
) -> tuple[AsyncApicurioRegistryClient, respx.MockRouter]:
    client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    return client, mock_registry


# ═══════════════════════════════════════════════════════════════
# schema_retrieval.feature steps
# ═══════════════════════════════════════════════════════════════


@given(
    parsers.cfparse(
        'the registry holds a known Avro schema for artifact "{artifact_id}" with global_id {global_id:d} and content_id {content_id:d}'
    ),
    target_fixture="schema_route",
)
def given_schema_for_artifact(
    async_client_and_registry: tuple[AsyncApicurioRegistryClient, respx.MockRouter],
    artifact_id: str,
    global_id: int,
    content_id: int,
) -> respx.Route:
    _, router = async_client_and_registry
    url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/{artifact_id}/versions/latest/content"
    return router.get(url).mock(
        return_value=Response(
            200,
            content=json.dumps(USER_EVENT_SCHEMA_JSON),
            headers={
                "X-Registry-GlobalId": str(global_id),
                "X-Registry-ContentId": str(content_id),
            },
        )
    )


@given(
    parsers.cfparse('the registry returns HTTP 404 for artifact "{artifact_id}"'),
)
def given_404_for_artifact(
    async_client_and_registry: tuple[AsyncApicurioRegistryClient, respx.MockRouter],
    artifact_id: str,
) -> None:
    _, router = async_client_and_registry
    url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/{artifact_id}/versions/latest/content"
    router.get(url).mock(return_value=Response(404))


@given("the registry is unreachable due to a network error")
def given_registry_unreachable(
    async_client_and_registry: tuple[AsyncApicurioRegistryClient, respx.MockRouter],
) -> None:
    _, router = async_client_and_registry
    router.get(url__startswith=f"{REGISTRY_URL}/groups/").mock(
        side_effect=httpx.ConnectError("Connection refused")
    )


@given(
    parsers.cfparse('the client is configured with group_id "{group_id}"'),
    target_fixture="async_client_and_registry",
)
def given_client_with_group_id(
    mock_registry: respx.MockRouter, group_id: str
) -> tuple[AsyncApicurioRegistryClient, respx.MockRouter]:
    client = AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=group_id)
    return client, mock_registry


@given(
    parsers.cfparse(
        'the registry holds a schema for artifact "{artifact_id}" in group "{group_id}"'
    ),
    target_fixture="tracked_route",
)
def given_schema_in_group(
    async_client_and_registry: tuple[AsyncApicurioRegistryClient, respx.MockRouter],
    artifact_id: str,
    group_id: str,
) -> respx.Route:
    _, router = async_client_and_registry
    url = f"{REGISTRY_URL}/groups/{group_id}/artifacts/{artifact_id}/versions/latest/content"
    return router.get(url).mock(
        return_value=Response(
            200,
            content=json.dumps(USER_EVENT_SCHEMA_JSON),
            headers={
                "X-Registry-GlobalId": str(GLOBAL_ID),
                "X-Registry-ContentId": str(CONTENT_ID),
            },
        )
    )


@when(
    parsers.cfparse('await client.get_schema("{artifact_id}") is called'),
    target_fixture="get_schema_result",
)
def when_get_schema(
    async_client_and_registry: tuple[AsyncApicurioRegistryClient, respx.MockRouter],
    artifact_id: str,
) -> CachedSchema | SchemaNotFoundError | RegistryConnectionError:
    client, _ = async_client_and_registry
    try:
        return asyncio.get_event_loop().run_until_complete(
            client.get_schema(artifact_id)
        )
    except (SchemaNotFoundError, RegistryConnectionError) as exc:
        return exc


@then("the returned CachedSchema contains the parsed Avro schema dict")
def then_schema_dict(get_schema_result: CachedSchema) -> None:
    assert isinstance(get_schema_result, CachedSchema)
    assert get_schema_result.schema == USER_EVENT_SCHEMA_JSON


@then(parsers.cfparse("the CachedSchema global_id is {global_id:d}"))
def then_global_id(get_schema_result: CachedSchema, global_id: int) -> None:
    assert get_schema_result.global_id == global_id


@then(parsers.cfparse("the CachedSchema content_id is {content_id:d}"))
def then_content_id(get_schema_result: CachedSchema, content_id: int) -> None:
    assert get_schema_result.content_id == content_id


@then("a SchemaNotFoundError is raised")
def then_schema_not_found(get_schema_result: SchemaNotFoundError) -> None:
    assert isinstance(get_schema_result, SchemaNotFoundError)


@then(
    parsers.cfparse(
        'the error identifies artifact "{artifact_id}" and the configured group_id'
    )
)
def then_error_identifies_artifact(
    get_schema_result: SchemaNotFoundError, artifact_id: str
) -> None:
    assert get_schema_result.artifact_id == artifact_id
    assert get_schema_result.group_id == GROUP_ID


@then("a RegistryConnectionError is raised")
def then_registry_connection_error(get_schema_result: RegistryConnectionError) -> None:
    assert isinstance(get_schema_result, RegistryConnectionError)


@then("the error wraps the underlying network exception")
def then_error_wraps_exception(get_schema_result: RegistryConnectionError) -> None:
    assert get_schema_result.__cause__ is not None


@then("the error includes the registry base URL")
def then_error_includes_url(get_schema_result: RegistryConnectionError) -> None:
    assert get_schema_result.url == REGISTRY_URL


@then(
    parsers.cfparse(
        'the HTTP request targets the endpoint for group "{group_id}" and artifact "{artifact_id}"'
    )
)
def then_request_targets_endpoint(
    tracked_route: respx.Route,
    group_id: str,
    artifact_id: str,
) -> None:
    assert tracked_route.call_count == 1


@then("the returned object is an instance of CachedSchema from apicurio_serdes._client")
def then_instance_of_cached_schema(get_schema_result: CachedSchema) -> None:
    assert type(get_schema_result) is CachedSchema


# ═══════════════════════════════════════════════════════════════
# schema_caching.feature steps
# ═══════════════════════════════════════════════════════════════


@given(
    parsers.cfparse('the registry holds a schema for artifact "{artifact_id}"'),
    target_fixture="cache_route",
)
def given_schema_for_caching(
    async_client_and_registry: tuple[AsyncApicurioRegistryClient, respx.MockRouter],
    artifact_id: str,
) -> respx.Route:
    _, router = async_client_and_registry
    url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/{artifact_id}/versions/latest/content"
    return router.get(url).mock(
        return_value=Response(
            200,
            content=json.dumps(USER_EVENT_SCHEMA_JSON),
            headers={
                "X-Registry-GlobalId": str(GLOBAL_ID),
                "X-Registry-ContentId": str(CONTENT_ID),
            },
        )
    )


SCHEMA_B_JSON: dict[str, Any] = {
    "type": "record",
    "name": "SchemaB",
    "namespace": "com.example",
    "fields": [{"name": "id", "type": "string"}],
}


@given(
    parsers.cfparse('the registry holds schemas for artifacts "{art_a}" and "{art_b}"'),
    target_fixture="two_routes",
)
def given_two_schemas(
    async_client_and_registry: tuple[AsyncApicurioRegistryClient, respx.MockRouter],
    art_a: str,
    art_b: str,
) -> dict[str, respx.Route]:
    _, router = async_client_and_registry
    url_a = (
        f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/{art_a}/versions/latest/content"
    )
    url_b = (
        f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/{art_b}/versions/latest/content"
    )
    route_a = router.get(url_a).mock(
        return_value=Response(
            200,
            content=json.dumps(USER_EVENT_SCHEMA_JSON),
            headers={"X-Registry-GlobalId": "10", "X-Registry-ContentId": "1"},
        )
    )
    route_b = router.get(url_b).mock(
        return_value=Response(
            200,
            content=json.dumps(SCHEMA_B_JSON),
            headers={"X-Registry-GlobalId": "20", "X-Registry-ContentId": "2"},
        )
    )
    return {"a": route_a, "b": route_b, "art_a": art_a, "art_b": art_b}  # type: ignore[dict-item]


@when(
    parsers.cfparse('await client.get_schema("{artifact_id}") is called a second time'),
    target_fixture="second_result",
)
def when_get_schema_second(
    async_client_and_registry: tuple[AsyncApicurioRegistryClient, respx.MockRouter],
    artifact_id: str,
) -> CachedSchema:
    client, _ = async_client_and_registry
    return asyncio.get_event_loop().run_until_complete(client.get_schema(artifact_id))


@then(
    parsers.cfparse(
        'the registry received exactly {count:d} HTTP request for "{artifact_id}"'
    )
)
def then_request_count(
    async_client_and_registry: tuple[AsyncApicurioRegistryClient, respx.MockRouter],
    count: int,
    artifact_id: str,
    cache_route: respx.Route | None = None,
    two_routes: dict[str, Any] | None = None,
) -> None:
    if cache_route is not None:
        assert cache_route.call_count == count
    elif two_routes is not None:
        if artifact_id == two_routes.get("art_a"):
            assert two_routes["a"].call_count == count
        else:
            assert two_routes["b"].call_count == count


@then("both calls returned the same CachedSchema")
def then_same_cached_schema(
    get_schema_result: CachedSchema, second_result: CachedSchema
) -> None:
    assert get_schema_result is second_result


@when(
    parsers.cfparse(
        '{n:d} coroutines concurrently call await client.get_schema("{artifact_id}") for the first time'
    ),
    target_fixture="concurrent_results",
)
def when_concurrent_get_schema(
    async_client_and_registry: tuple[AsyncApicurioRegistryClient, respx.MockRouter],
    n: int,
    artifact_id: str,
) -> list[CachedSchema]:
    client, _ = async_client_and_registry

    async def gather_results() -> list[CachedSchema]:
        return list(
            await asyncio.gather(*[client.get_schema(artifact_id) for _ in range(n)])
        )

    return asyncio.get_event_loop().run_until_complete(gather_results())


@then("all coroutines received an identical CachedSchema")
def then_all_identical(concurrent_results: list[CachedSchema]) -> None:
    assert all(r is concurrent_results[0] for r in concurrent_results)


# ═══════════════════════════════════════════════════════════════
# interface_compatibility.feature steps
# ═══════════════════════════════════════════════════════════════


@given(
    parsers.cfparse(
        'the sync client is constructed with AsyncApicurioRegistryClient(url="{url}", group_id="{group_id}")'
    ),
    target_fixture="constructor_params",
)
def given_sync_constructor_params(url: str, group_id: str) -> dict[str, str]:
    return {"url": url, "group_id": group_id}


@when(
    "AsyncApicurioRegistryClient is constructed with the same url and group_id",
    target_fixture="async_instance",
)
def when_async_constructed(
    constructor_params: dict[str, str],
) -> AsyncApicurioRegistryClient:
    return AsyncApicurioRegistryClient(**constructor_params)


@then("the async client is initialised successfully with those parameters")
def then_async_initialised(
    async_instance: AsyncApicurioRegistryClient, constructor_params: dict[str, str]
) -> None:
    assert async_instance.url == constructor_params["url"]
    assert async_instance.group_id == constructor_params["group_id"]


@given("an AsyncApicurioRegistryClient instance", target_fixture="async_instance")
def given_async_instance(
    mock_registry: respx.MockRouter,
) -> AsyncApicurioRegistryClient:
    return AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)


@when(
    "the developer calls await client.get_schema(artifact_id) instead of client.get_schema(artifact_id)",
    target_fixture="async_method_result",
)
def when_async_get_schema_called(
    async_instance: AsyncApicurioRegistryClient,
    mock_registry: respx.MockRouter,
) -> CachedSchema:
    url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/TestArtifact/versions/latest/content"
    mock_registry.get(url).mock(
        return_value=Response(
            200,
            content=json.dumps(USER_EVENT_SCHEMA_JSON),
            headers={
                "X-Registry-GlobalId": str(GLOBAL_ID),
                "X-Registry-ContentId": str(CONTENT_ID),
            },
        )
    )
    return asyncio.get_event_loop().run_until_complete(
        async_instance.get_schema("TestArtifact")
    )


@then(
    "the async client responds with the same CachedSchema return type as the sync client"
)
def then_same_return_type(async_method_result: CachedSchema) -> None:
    assert type(async_method_result) is CachedSchema


@given("a configured AsyncApicurioRegistryClient", target_fixture="async_error_client")
def given_configured_async_client(
    mock_registry: respx.MockRouter,
) -> tuple[AsyncApicurioRegistryClient, respx.MockRouter]:
    return AsyncApicurioRegistryClient(
        url=REGISTRY_URL, group_id=GROUP_ID
    ), mock_registry


@when(
    parsers.cfparse("a {condition} occurs during get_schema"),
    target_fixture="error_result",
)
def when_error_condition(
    async_error_client: tuple[AsyncApicurioRegistryClient, respx.MockRouter],
    condition: str,
) -> Exception:
    client, router = async_error_client
    if condition == "registry returns HTTP 404":
        url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/err/versions/latest/content"
        router.get(url).mock(return_value=Response(404))
    else:
        router.get(url__startswith=f"{REGISTRY_URL}/groups/").mock(
            side_effect=httpx.ConnectError("refused")
        )
    try:
        asyncio.get_event_loop().run_until_complete(client.get_schema("err"))
    except Exception as exc:
        return exc
    raise AssertionError("Expected an exception")


@then(
    parsers.cfparse(
        "a {error_type} is raised with the same attributes as the sync client equivalent"
    )
)
def then_error_type_matches(error_result: Exception, error_type: str) -> None:
    if error_type == "SchemaNotFoundError":
        assert isinstance(error_result, SchemaNotFoundError)
        assert hasattr(error_result, "group_id")
        assert hasattr(error_result, "artifact_id")
    else:
        assert isinstance(error_result, RegistryConnectionError)
        assert hasattr(error_result, "url")


@when(
    "the developer runs: from apicurio_serdes import AsyncApicurioRegistryClient",
    target_fixture="import_result",
)
def when_import() -> type:
    from apicurio_serdes import AsyncApicurioRegistryClient as Imported

    return Imported


@then("the import succeeds without error")
def then_import_succeeds(import_result: type) -> None:
    assert import_result is not None


@then(
    "AsyncApicurioRegistryClient is the same class as apicurio_serdes._async_client.AsyncApicurioRegistryClient"
)
def then_same_class(import_result: type) -> None:
    assert import_result is AsyncApicurioRegistryClient


# ═══════════════════════════════════════════════════════════════
# lifecycle_management.feature steps
# ═══════════════════════════════════════════════════════════════


@when(
    'it is used as "async with AsyncApicurioRegistryClient(...) as client:"',
    target_fixture="context_client",
)
def when_used_as_context_manager(
    async_instance: AsyncApicurioRegistryClient,
) -> AsyncApicurioRegistryClient:
    asyncio.get_event_loop().run_until_complete(async_instance.__aenter__())
    return async_instance


@when("the async with block exits normally", target_fixture="closed_client")
def when_block_exits_normally(
    context_client: AsyncApicurioRegistryClient,
) -> AsyncApicurioRegistryClient:
    asyncio.get_event_loop().run_until_complete(
        context_client.__aexit__(None, None, None)
    )
    return context_client


@then("the underlying httpx.AsyncClient is closed")
def then_http_client_closed(closed_client: AsyncApicurioRegistryClient) -> None:
    assert closed_client._http_client.is_closed is True


@when(
    "an exception is raised inside the async with block", target_fixture="closed_client"
)
def when_exception_in_block(
    context_client: AsyncApicurioRegistryClient,
) -> AsyncApicurioRegistryClient:
    try:
        raise RuntimeError("simulated error")
    except RuntimeError:
        import sys

        exc_info = sys.exc_info()
        asyncio.get_event_loop().run_until_complete(
            context_client.__aexit__(exc_info[0], exc_info[1], exc_info[2])
        )
    return context_client


@then("the underlying httpx.AsyncClient is closed before the exception propagates")
def then_closed_before_propagation(closed_client: AsyncApicurioRegistryClient) -> None:
    assert closed_client._http_client.is_closed is True


@given(
    "an AsyncApicurioRegistryClient instance created without a context manager",
    target_fixture="standalone_client",
)
def given_standalone_client() -> AsyncApicurioRegistryClient:
    return AsyncApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)


@when("await client.aclose() is called", target_fixture="closed_client")
def when_aclose_called(
    standalone_client: AsyncApicurioRegistryClient,
) -> AsyncApicurioRegistryClient:
    asyncio.get_event_loop().run_until_complete(standalone_client.aclose())
    return standalone_client


# ═══════════════════════════════════════════════════════════════
# validation.feature steps
# ═══════════════════════════════════════════════════════════════


@when(
    parsers.re(
        r'AsyncApicurioRegistryClient is constructed with url="(?P<url>.*)" and group_id="(?P<group_id>.*)"'
    ),
    target_fixture="validation_error",
)
def when_constructed_with_invalid_params(url: str, group_id: str) -> ValueError:
    with pytest.raises(ValueError) as exc_info:
        AsyncApicurioRegistryClient(url=url, group_id=group_id)
    return exc_info.value


@then(parsers.re(r'a ValueError is raised with message "(?P<message>.*)"'))
def then_value_error_message(validation_error: ValueError, message: str) -> None:
    assert str(validation_error) == message
