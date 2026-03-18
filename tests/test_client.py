"""Step definitions for TS-008, TS-010, TS-011, TS-012: ApicurioRegistryClient scenarios."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx
import pytest
import respx
from pytest_bdd import given, parsers, scenario, then, when

from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroSerializer
from apicurio_serdes.serialization import MessageField, SerializationContext
from tests.conftest import (
    CONTENT_ID,
    GLOBAL_ID,
    GROUP_ID,
    REGISTRY_URL,
    USER_EVENT_SCHEMA_JSON,
    VALID_USER_EVENT,
    VALID_USER_EVENT_ALT,
    _id_not_found_route,
    _id_schema_route,
    _register_error_route,
    _register_route,
    _schema_route,
)

AVRO_FEATURE = "../specs/001-avro-serializer/tests/features/avro_serialization.feature"
CACHE_FEATURE = "../specs/001-avro-serializer/tests/features/schema_caching.feature"


# ── Scenarios ──


@scenario(AVRO_FEATURE, "group_id is a required parameter for ApicurioRegistryClient")
def test_group_id_required() -> None:
    """TS-008."""


@scenario(
    CACHE_FEATURE,
    "Registry is contacted exactly once when the same artifact is serialized multiple times",
)
def test_ts010_cache_single_artifact() -> None:
    """TS-010."""


@scenario(
    CACHE_FEATURE,
    "A new artifact triggers one registry call without re-fetching a previously cached schema",
)
def test_ts011_cache_multiple_artifacts() -> None:
    """TS-011."""


@scenario(
    CACHE_FEATURE,
    "Concurrent calls to the same artifact result in exactly one registry HTTP request",
)
def test_ts012_concurrent_cache() -> None:
    """TS-012."""


# ── TS-008 steps ──


@when(
    "an ApicurioRegistryClient is constructed without providing a group_id",
    target_fixture="construction_error",
)
def when_client_without_group_id() -> ValueError:
    with pytest.raises(ValueError) as exc_info:
        ApicurioRegistryClient(url="http://registry:8080/apis/registry/v3", group_id="")
    return exc_info.value


@then("a ValueError is raised indicating that group_id is required")
def then_value_error_raised(construction_error: ValueError) -> None:
    assert "group_id" in str(construction_error)


# ── Schema caching Background ──

SCHEMA_B_JSON: dict[str, Any] = {
    "type": "record",
    "name": "SchemaB",
    "namespace": "com.example",
    "fields": [
        {"name": "id", "type": "string"},
    ],
}


@given(
    parsers.cfparse(
        'a configured ApicurioRegistryClient pointing at a registry that holds schemas for artifacts "{art_a}" and "{art_b}"'
    ),
    target_fixture="registry_client",
)
def given_client_two_schemas(
    mock_registry: respx.MockRouter, art_a: str, art_b: str
) -> ApicurioRegistryClient:
    _schema_route(mock_registry, art_a, global_id=10, content_id=1)
    _schema_route(
        mock_registry, art_b, schema=SCHEMA_B_JSON, global_id=20, content_id=2
    )
    return ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)


@given(
    parsers.cfparse('an AvroSerializer configured for artifact "{artifact_id}"'),
    target_fixture="serializer",
)
def given_serializer_for_caching(
    registry_client: ApicurioRegistryClient, artifact_id: str
) -> AvroSerializer:
    return AvroSerializer(registry_client=registry_client, artifact_id=artifact_id)


@given(
    parsers.cfparse('a SerializationContext for topic "{topic}" and field {field}'),
    target_fixture="ctx",
)
def given_ctx(topic: str, field: str) -> SerializationContext:
    return SerializationContext(topic=topic, field=MessageField[field])


# ── TS-010 steps ──


@when(
    "the serializer is called twice in sequence with valid dicts",
    target_fixture="two_calls_result",
)
def when_serialize_twice(
    serializer: AvroSerializer, ctx: SerializationContext
) -> tuple[bytes, bytes]:
    return serializer(VALID_USER_EVENT, ctx), serializer(VALID_USER_EVENT_ALT, ctx)


@then(
    parsers.cfparse(
        'the registry is contacted exactly once for artifact "{artifact_id}"'
    )
)
def then_contacted_once(mock_registry: respx.MockRouter, artifact_id: str) -> None:
    call_count = 0
    for route in mock_registry.routes:
        if hasattr(route, "pattern") and artifact_id in str(route.pattern):
            call_count = route.call_count
            break
    assert call_count == 1, f"Expected 1 call for {artifact_id}, got {call_count}"


# ── TS-011 steps ──


@given(
    parsers.cfparse(
        'an AvroSerializer for artifact "{artifact_id}" that has already fetched and cached its schema'
    ),
    target_fixture="serializer_a",
)
def given_serializer_already_cached(
    registry_client: ApicurioRegistryClient, artifact_id: str
) -> AvroSerializer:
    serializer = AvroSerializer(
        registry_client=registry_client, artifact_id=artifact_id
    )
    ctx = SerializationContext(topic="warmup", field=MessageField.VALUE)
    serializer(VALID_USER_EVENT, ctx)
    return serializer


@given(
    parsers.cfparse('an AvroSerializer for artifact "{artifact_id}"'),
    target_fixture="serializer_b",
)
def given_serializer_b(
    registry_client: ApicurioRegistryClient, artifact_id: str
) -> AvroSerializer:
    return AvroSerializer(registry_client=registry_client, artifact_id=artifact_id)


@when(
    parsers.cfparse(
        'the serializer for "{artifact_id}" is used for the first time with a valid dict'
    ),
    target_fixture="first_call_result",
)
def when_serializer_b_first_call(
    serializer_b: AvroSerializer, ctx: SerializationContext, artifact_id: str
) -> bytes:
    data_b = {"id": "test-123"}
    return serializer_b(data_b, ctx)


@then(
    parsers.cfparse('the registry is not contacted again for artifact "{artifact_id}"')
)
def then_not_contacted_again(mock_registry: respx.MockRouter, artifact_id: str) -> None:
    for route in mock_registry.routes:
        if hasattr(route, "pattern") and artifact_id in str(route.pattern):
            assert route.call_count == 1, (
                f"Expected exactly 1 call for {artifact_id}, got {route.call_count}"
            )
            return
    # If no matching route found, that's fine (never called)


# ── TS-012 steps ──


@given(
    parsers.cfparse(
        'an ApicurioRegistryClient pointing at a registry that holds a schema for artifact "{artifact_id}"'
    ),
    target_fixture="registry_client",
)
def given_client_single_schema(
    mock_registry: respx.MockRouter, artifact_id: str
) -> ApicurioRegistryClient:
    _schema_route(mock_registry, artifact_id)
    return ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)


@given(
    parsers.cfparse(
        'multiple AvroSerializer instances all configured for artifact "{artifact_id}"'
    ),
    target_fixture="serializers",
)
def given_multiple_serializers(
    registry_client: ApicurioRegistryClient, artifact_id: str
) -> list[AvroSerializer]:
    return [
        AvroSerializer(registry_client=registry_client, artifact_id=artifact_id)
        for _ in range(10)
    ]


@when(
    "all serializers are called concurrently with valid dicts",
    target_fixture="concurrent_results",
)
def when_concurrent_calls(
    serializers: list[AvroSerializer],
) -> list[bytes]:
    ctx = SerializationContext(topic="concurrent", field=MessageField.VALUE)
    with ThreadPoolExecutor(max_workers=len(serializers)) as pool:
        futures = [pool.submit(s, VALID_USER_EVENT, ctx) for s in serializers]
        return [f.result() for f in futures]


@then("all serializers return valid Confluent-framed Avro bytes")
def then_all_valid(concurrent_results: list[bytes]) -> None:
    for result in concurrent_results:
        assert result[0:1] == b"\x00"
        assert len(result) > 5


# ── Additional coverage tests ──


def test_empty_url_raises_value_error() -> None:
    """Empty url must raise ValueError."""
    with pytest.raises(ValueError, match="url"):
        ApicurioRegistryClient(url="", group_id="g")


def test_get_schema_500_raises_registry_connection_error(
    mock_registry: respx.MockRouter,
) -> None:
    """Unexpected HTTP status in get_schema raises RegistryConnectionError [FR-013]."""
    from httpx import Response

    from apicurio_serdes._errors import RegistryConnectionError

    url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/Broken/versions/latest/content"
    mock_registry.get(url).mock(return_value=Response(500))
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(RegistryConnectionError):
        client.get_schema("Broken")


def test_get_schema_by_global_id_500_raises_registry_connection_error(
    mock_registry: respx.MockRouter,
) -> None:
    """Unexpected HTTP status in _get_schema_by_id raises RegistryConnectionError [FR-013]."""
    from httpx import Response

    from apicurio_serdes._errors import RegistryConnectionError

    mock_registry.get(url__startswith=f"{REGISTRY_URL}/ids/globalIds/").mock(
        return_value=Response(500)
    )
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(RegistryConnectionError):
        client.get_schema_by_global_id(7)


# ── T004: get_schema_by_global_id ──


def test_get_schema_by_global_id_cache_miss(mock_registry: respx.MockRouter) -> None:
    """First call hits registry and returns schema dict [TS-017, FR-007]."""
    _id_schema_route(mock_registry, "globalId", 7)
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    result = client.get_schema_by_global_id(7)
    assert result == USER_EVENT_SCHEMA_JSON


def test_get_schema_by_global_id_cache_hit(mock_registry: respx.MockRouter) -> None:
    """Second call returns cached result without HTTP call [FR-007]."""
    route = _id_schema_route(mock_registry, "globalId", 7)
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    r1 = client.get_schema_by_global_id(7)
    r2 = client.get_schema_by_global_id(7)
    assert r1 == r2
    assert route.call_count == 1


def test_get_schema_by_global_id_not_found(mock_registry: respx.MockRouter) -> None:
    """404 raises SchemaNotFoundError with id_type/id_value [FR-010]."""
    from apicurio_serdes._errors import SchemaNotFoundError

    _id_not_found_route(mock_registry, "globalId", 999)
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(SchemaNotFoundError) as exc_info:
        client.get_schema_by_global_id(999)
    err = exc_info.value
    assert err.id_type == "globalId"
    assert err.id_value == 999


def test_get_schema_by_global_id_network_error(mock_registry: respx.MockRouter) -> None:
    """Network failure raises RegistryConnectionError [FR-012]."""
    from apicurio_serdes._errors import RegistryConnectionError

    mock_registry.get(url__startswith=f"{REGISTRY_URL}/ids/globalIds/").mock(
        side_effect=httpx.ConnectError("refused")
    )
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(RegistryConnectionError):
        client.get_schema_by_global_id(7)


# ── T005: get_schema_by_content_id ──


def test_get_schema_by_content_id_cache_miss(mock_registry: respx.MockRouter) -> None:
    """First call hits registry and returns schema dict [TS-016, FR-007]."""
    _id_schema_route(mock_registry, "contentId", 42)
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    result = client.get_schema_by_content_id(42)
    assert result == USER_EVENT_SCHEMA_JSON


def test_get_schema_by_content_id_cache_hit(mock_registry: respx.MockRouter) -> None:
    """Second call returns cached result without HTTP call [FR-007]."""
    route = _id_schema_route(mock_registry, "contentId", 42)
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    r1 = client.get_schema_by_content_id(42)
    r2 = client.get_schema_by_content_id(42)
    assert r1 == r2
    assert route.call_count == 1


def test_get_schema_by_content_id_not_found(mock_registry: respx.MockRouter) -> None:
    """404 raises SchemaNotFoundError with id_type/id_value [FR-010]."""
    from apicurio_serdes._errors import SchemaNotFoundError

    _id_not_found_route(mock_registry, "contentId", 9999)
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(SchemaNotFoundError) as exc_info:
        client.get_schema_by_content_id(9999)
    err = exc_info.value
    assert err.id_type == "contentId"
    assert err.id_value == 9999


def test_get_schema_by_content_id_network_error(
    mock_registry: respx.MockRouter,
) -> None:
    """Network failure raises RegistryConnectionError [FR-012]."""
    from apicurio_serdes._errors import RegistryConnectionError

    mock_registry.get(url__startswith=f"{REGISTRY_URL}/ids/contentIds/").mock(
        side_effect=httpx.ConnectError("refused")
    )
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(RegistryConnectionError):
        client.get_schema_by_content_id(42)


def test_double_check_locking_cache_hit(mock_registry: respx.MockRouter) -> None:
    """Exercise the double-checked locking return path (line 80).

    Simulates a race where another thread populates the cache between
    the fast-path check (line 74) and the lock-guarded check (line 79).
    """
    from apicurio_serdes._client import CachedSchema

    _schema_route(mock_registry, "Race")
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)

    cached = CachedSchema(
        schema={"type": "record", "name": "X", "fields": []},
        global_id=99,
        content_id=88,
    )
    cache_key = (GROUP_ID, "Race")
    check_count: dict[str, int] = {"n": 0}

    class _RaceDict(dict[tuple[str, str], Any]):
        """Dict that misses the first __contains__ then simulates a race fill."""

        def __contains__(self, key: object) -> bool:
            if key == cache_key:
                check_count["n"] += 1
                if check_count["n"] == 1:
                    return False  # fast-path miss
                # Inside the lock: simulate another thread having filled cache
                self[cache_key] = cached  # type: ignore[index]
                return True
            return super().__contains__(key)

    client._schema_cache = _RaceDict()  # type: ignore[assignment]
    result = client.get_schema("Race")
    assert result is cached


def test_global_id_outside_int64_raises_value_error(
    mock_registry: respx.MockRouter,
) -> None:
    """Registry returning a globalId outside signed 64-bit range raises ValueError."""
    import json

    from httpx import Response

    from tests.conftest import USER_EVENT_SCHEMA_JSON

    url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/OverflowTest/versions/latest/content"
    mock_registry.get(url).mock(
        return_value=Response(
            200,
            content=json.dumps(USER_EVENT_SCHEMA_JSON),
            headers={
                "X-Registry-GlobalId": str(2**63),  # outside int64 range
                "X-Registry-ContentId": "1",
            },
        )
    )
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(ValueError, match="globalId"):
        client.get_schema("OverflowTest")


def test_context_manager_closes_client(mock_registry: respx.MockRouter) -> None:
    """Context manager __enter__ returns self and __exit__ closes the HTTP client."""
    _schema_route(mock_registry, "UserEvent")
    with ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID) as client:
        assert isinstance(client, ApicurioRegistryClient)
        result = client.get_schema("UserEvent")
        assert result.schema == USER_EVENT_SCHEMA_JSON
    # After the with-block, the underlying httpx.Client should be closed.
    assert client._http_client.is_closed


def test_content_id_outside_int64_raises_value_error(
    mock_registry: respx.MockRouter,
) -> None:
    """Registry returning a contentId outside signed 64-bit range raises ValueError."""
    import json

    from httpx import Response

    from tests.conftest import USER_EVENT_SCHEMA_JSON

    url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/OverflowTest2/versions/latest/content"
    mock_registry.get(url).mock(
        return_value=Response(
            200,
            content=json.dumps(USER_EVENT_SCHEMA_JSON),
            headers={
                "X-Registry-GlobalId": "1",
                "X-Registry-ContentId": str(2**63),  # outside int64 range
            },
        )
    )
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(ValueError, match="contentId"):
        client.get_schema("OverflowTest2")


def test_get_schema_after_close_raises_runtime_error(
    mock_registry: respx.MockRouter,
) -> None:
    """get_schema on a closed client raises RuntimeError."""
    _schema_route(mock_registry, "UserEvent")
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    client.close()
    with pytest.raises(RuntimeError, match="closed"):
        client.get_schema("UserEvent")


def test_get_schema_by_global_id_after_close_raises_runtime_error(
    mock_registry: respx.MockRouter,
) -> None:
    """get_schema_by_global_id on a closed client raises RuntimeError."""
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    client.close()
    with pytest.raises(RuntimeError, match="closed"):
        client.get_schema_by_global_id(7)


def test_context_manager_prevents_use_after_exit(
    mock_registry: respx.MockRouter,
) -> None:
    """After exiting context manager, client raises RuntimeError."""
    _schema_route(mock_registry, "UserEvent")
    with ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID) as client:
        client.get_schema("UserEvent")
    with pytest.raises(RuntimeError, match="closed"):
        client.get_schema("UserEvent")


def test_get_schema_read_timeout_raises_registry_connection_error(
    mock_registry: respx.MockRouter,
) -> None:
    """httpx.ReadTimeout (not ConnectError) raises RegistryConnectionError [TD-001]."""
    from apicurio_serdes._errors import RegistryConnectionError

    mock_registry.get(
        url__startswith=f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/"
    ).mock(side_effect=httpx.ReadTimeout("timed out"))
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(RegistryConnectionError):
        client.get_schema("Slow")


def test_get_schema_by_global_id_read_timeout_raises_registry_connection_error(
    mock_registry: respx.MockRouter,
) -> None:
    """httpx.ReadTimeout in _get_schema_by_id raises RegistryConnectionError [TD-001]."""
    from apicurio_serdes._errors import RegistryConnectionError

    mock_registry.get(url__startswith=f"{REGISTRY_URL}/ids/globalIds/").mock(
        side_effect=httpx.ReadTimeout("timed out")
    )
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(RegistryConnectionError):
        client.get_schema_by_global_id(7)


# ── register_schema tests ──


def test_register_schema_happy_path(mock_registry: respx.MockRouter) -> None:
    """register_schema returns a CachedSchema with correct IDs."""
    from apicurio_serdes._base import CachedSchema

    _register_route(mock_registry, "UserEvent")
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    result = client.register_schema("UserEvent", USER_EVENT_SCHEMA_JSON)
    assert isinstance(result, CachedSchema)
    assert result.schema == USER_EVENT_SCHEMA_JSON
    assert result.global_id == GLOBAL_ID
    assert result.content_id == CONTENT_ID


def test_register_schema_populates_cache(mock_registry: respx.MockRouter) -> None:
    """After register_schema, get_schema is a cache hit (zero HTTP calls)."""
    _register_route(mock_registry, "UserEvent")
    get_route = _schema_route(mock_registry, "UserEvent")
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    client.register_schema("UserEvent", USER_EVENT_SCHEMA_JSON)
    client.get_schema("UserEvent")
    assert get_route.call_count == 0


@pytest.mark.parametrize(
    "if_exists", ["FAIL", "CREATE_VERSION", "FIND_OR_CREATE_VERSION"]
)
def test_register_schema_forwards_if_exists(
    mock_registry: respx.MockRouter, if_exists: str
) -> None:
    """register_schema forwards if_exists as ifExists query param."""
    route = _register_route(mock_registry, "UserEvent", if_exists=if_exists)
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    client.register_schema("UserEvent", USER_EVENT_SCHEMA_JSON, if_exists=if_exists)
    assert route.call_count == 1


def test_register_schema_default_if_exists_is_find_or_create_version(
    mock_registry: respx.MockRouter,
) -> None:
    """Default if_exists is 'FIND_OR_CREATE_VERSION', forwarded as ifExists=FIND_OR_CREATE_VERSION."""
    route = _register_route(
        mock_registry, "UserEvent", if_exists="FIND_OR_CREATE_VERSION"
    )
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    client.register_schema("UserEvent", USER_EVENT_SCHEMA_JSON)
    assert route.call_count == 1


def test_register_schema_409_raises_schema_registration_error(
    mock_registry: respx.MockRouter,
) -> None:
    """409 Conflict raises SchemaRegistrationError with artifact_id."""
    from apicurio_serdes._errors import SchemaRegistrationError

    _register_error_route(mock_registry, 409)
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(SchemaRegistrationError) as exc_info:
        client.register_schema("UserEvent", USER_EVENT_SCHEMA_JSON)
    assert exc_info.value.artifact_id == "UserEvent"


def test_register_schema_500_raises_schema_registration_error(
    mock_registry: respx.MockRouter,
) -> None:
    """500 raises SchemaRegistrationError."""
    from apicurio_serdes._errors import SchemaRegistrationError

    _register_error_route(mock_registry, 500)
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(SchemaRegistrationError):
        client.register_schema("UserEvent", USER_EVENT_SCHEMA_JSON)


def test_register_schema_network_error_raises_registry_connection_error(
    mock_registry: respx.MockRouter,
) -> None:
    """Network failure raises RegistryConnectionError."""
    from apicurio_serdes._errors import RegistryConnectionError

    mock_registry.post(
        url__startswith=f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts"
    ).mock(side_effect=httpx.ConnectError("refused"))
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(RegistryConnectionError):
        client.register_schema("UserEvent", USER_EVENT_SCHEMA_JSON)


def test_register_schema_after_close_raises_runtime_error(
    mock_registry: respx.MockRouter,
) -> None:
    """register_schema on a closed client raises RuntimeError."""
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    client.close()
    with pytest.raises(RuntimeError, match="closed"):
        client.register_schema("UserEvent", USER_EVENT_SCHEMA_JSON)


def test_register_schema_global_id_outside_int64_raises_value_error(
    mock_registry: respx.MockRouter,
) -> None:
    """register_schema with overflow globalId in response body raises ValueError."""
    from httpx import Response

    url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts"
    mock_registry.post(url).mock(
        return_value=Response(
            200,
            json={
                "artifact": {},
                "version": {
                    "globalId": 2**63,  # outside int64 range
                    "contentId": 1,
                },
            },
        )
    )
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(ValueError, match="globalId"):
        client.register_schema("UserEvent", USER_EVENT_SCHEMA_JSON)


def test_register_schema_content_id_outside_int64_raises_value_error(
    mock_registry: respx.MockRouter,
) -> None:
    """register_schema with overflow contentId in response body raises ValueError."""
    from httpx import Response

    url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts"
    mock_registry.post(url).mock(
        return_value=Response(
            200,
            json={
                "artifact": {},
                "version": {
                    "globalId": 1,
                    "contentId": 2**63,  # outside int64 range
                },
            },
        )
    )
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(ValueError, match="contentId"):
        client.register_schema("UserEvent", USER_EVENT_SCHEMA_JSON)


def test_register_schema_missing_version_key_raises_schema_registration_error(
    mock_registry: respx.MockRouter,
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
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(SchemaRegistrationError):
        client.register_schema("UserEvent", USER_EVENT_SCHEMA_JSON)


def test_register_schema_fast_path_cache_hit(mock_registry: respx.MockRouter) -> None:
    """Pre-populated cache means register_schema never POSTs."""
    from apicurio_serdes._base import CachedSchema

    cached = CachedSchema(schema=USER_EVENT_SCHEMA_JSON, global_id=99, content_id=88)
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    client._schema_cache[(GROUP_ID, "UserEvent")] = cached
    result = client.register_schema("UserEvent", USER_EVENT_SCHEMA_JSON)
    assert result is cached


def test_register_schema_double_check_locking(mock_registry: respx.MockRouter) -> None:
    """Exercise the inner double-check path for register_schema.

    Simulates a race where another thread populates the cache between
    the fast-path check and the lock-guarded check.
    """
    from apicurio_serdes._base import CachedSchema

    cached = CachedSchema(schema=USER_EVENT_SCHEMA_JSON, global_id=99, content_id=88)
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)

    cache_key = (GROUP_ID, "UserEvent")
    check_count: dict[str, int] = {"n": 0}

    class _RaceDict(dict[tuple[str, str], Any]):
        def __contains__(self, key: object) -> bool:
            if key == cache_key:
                check_count["n"] += 1
                if check_count["n"] == 1:
                    return False  # fast-path miss
                self[cache_key] = cached  # type: ignore[index]
                return True
            return super().__contains__(key)

    client._schema_cache = _RaceDict()  # type: ignore[assignment]
    result = client.register_schema("UserEvent", USER_EVENT_SCHEMA_JSON)
    assert result is cached


def test_id_cache_double_check_locking(mock_registry: respx.MockRouter) -> None:
    """Exercise the double-checked locking return path for _id_cache (line 156).

    Simulates a race where another thread populates the ID cache between
    the fast-path check and the lock-guarded check.
    """
    _id_schema_route(mock_registry, "contentId", 42)
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)

    cached_schema: dict[str, Any] = {"type": "record", "name": "X", "fields": []}
    cache_key = ("contentId", 42)
    check_count: dict[str, int] = {"n": 0}

    class _RaceDict(dict[tuple[str, int], Any]):
        """Dict that misses the first __contains__ then simulates a race fill."""

        def __contains__(self, key: object) -> bool:
            if key == cache_key:
                check_count["n"] += 1
                if check_count["n"] == 1:
                    return False  # fast-path miss
                self[cache_key] = cached_schema  # type: ignore[index]
                return True
            return super().__contains__(key)

    client._id_cache = _RaceDict()  # type: ignore[assignment]
    result = client.get_schema_by_content_id(42)
    assert result is cached_schema


# ── Auth wiring tests ──


def test_client_auth_defaults_to_none() -> None:
    """auth parameter defaults to None; existing tests unaffected."""
    import inspect

    params = inspect.signature(ApicurioRegistryClient.__init__).parameters
    assert "auth" in params
    assert params["auth"].default is None


def test_client_accepts_bearer_auth(mock_registry: respx.MockRouter) -> None:
    """ApicurioRegistryClient accepts auth=BearerAuth and passes it to httpx."""
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
    client = ApicurioRegistryClient(
        url=REGISTRY_URL, group_id=GROUP_ID, auth=BearerAuth(token="wire-tok")
    )
    client.get_schema("Auth")
    assert route.calls[0].request.headers["authorization"] == "Bearer wire-tok"


# ── Retry and escape hatch tests (#37) ──


import json
from unittest.mock import MagicMock, patch


def _flaky_schema_handler(n_failures: int) -> Any:
    """Side-effect handler: raises ConnectError n_failures times, then returns 200."""
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


def _flaky_status_schema_handler(fail_status: int, n_failures: int) -> Any:
    """Side-effect handler: returns fail_status n_failures times, then returns 200."""
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


def _flaky_id_handler(n_failures: int) -> Any:
    """Side-effect: ConnectError n times then valid schema response (ID endpoint)."""
    count = 0

    def _handler(request: httpx.Request) -> httpx.Response:
        nonlocal count
        count += 1
        if count <= n_failures:
            raise httpx.ConnectError("transient failure")
        return httpx.Response(
            200, content=json.dumps(USER_EVENT_SCHEMA_JSON).encode()
        )

    return _handler


def _flaky_register_handler(n_failures: int) -> Any:
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


def test_init_default_max_retries() -> None:
    """Default max_retries is 3."""
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    assert client.max_retries == 3


def test_init_default_retry_backoff_ms() -> None:
    """Default retry_backoff_ms is 1000."""
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    assert client.retry_backoff_ms == 1000


def test_init_default_retry_max_backoff_ms() -> None:
    """Default retry_max_backoff_ms is 20000."""
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    assert client.retry_max_backoff_ms == 20000


def test_init_custom_max_retries() -> None:
    """Custom max_retries is stored."""
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID, max_retries=5)
    assert client.max_retries == 5


def test_init_max_retries_zero_valid() -> None:
    """max_retries=0 disables retries without error."""
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID, max_retries=0)
    assert client.max_retries == 0


def test_init_max_retries_negative_raises_value_error() -> None:
    """max_retries=-1 raises ValueError."""
    with pytest.raises(ValueError, match="max_retries"):
        ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID, max_retries=-1)


# Retry on transport error


def test_get_schema_retries_on_connect_error_then_succeeds(
    mock_registry: respx.MockRouter,
) -> None:
    """ConnectError on first attempt retried; schema returned on second attempt."""
    url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/UserEvent/versions/latest/content"
    mock_registry.get(url).mock(side_effect=_flaky_schema_handler(1))
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with patch("apicurio_serdes._client.time.sleep"):
        result = client.get_schema("UserEvent")
    assert result.schema == USER_EVENT_SCHEMA_JSON


def test_get_schema_exhausts_retries_raises_connection_error(
    mock_registry: respx.MockRouter,
) -> None:
    """ConnectError on all attempts raises RegistryConnectionError after max_retries."""
    from apicurio_serdes._errors import RegistryConnectionError

    url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/UserEvent/versions/latest/content"
    route = mock_registry.get(url).mock(side_effect=_flaky_schema_handler(99))
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID, max_retries=2)
    with patch("apicurio_serdes._client.time.sleep"):
        with pytest.raises(RegistryConnectionError):
            client.get_schema("UserEvent")
    assert route.call_count == 3  # 1 initial + 2 retries


def test_get_schema_by_global_id_retries_on_connect_error(
    mock_registry: respx.MockRouter,
) -> None:
    """ID lookup retried on ConnectError."""
    mock_registry.get(
        url__startswith=f"{REGISTRY_URL}/ids/globalIds/"
    ).mock(side_effect=_flaky_id_handler(1))
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with patch("apicurio_serdes._client.time.sleep"):
        result = client.get_schema_by_global_id(GLOBAL_ID)
    assert result == USER_EVENT_SCHEMA_JSON


def test_register_schema_retries_on_connect_error(
    mock_registry: respx.MockRouter,
) -> None:
    """register_schema retried on ConnectError."""
    mock_registry.post(
        url__startswith=f"{REGISTRY_URL}/groups/"
    ).mock(side_effect=_flaky_register_handler(1))
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with patch("apicurio_serdes._client.time.sleep"):
        result = client.register_schema("UserEvent", USER_EVENT_SCHEMA_JSON)
    assert result.global_id == GLOBAL_ID


# Retry on retryable HTTP status codes


@pytest.mark.parametrize("fail_status", [429, 502, 503, 504])
def test_get_schema_retries_on_retryable_status(
    mock_registry: respx.MockRouter, fail_status: int
) -> None:
    """Schema GET retried on 429/502/503/504, succeeds on next attempt."""
    url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/UserEvent/versions/latest/content"
    mock_registry.get(url).mock(
        side_effect=_flaky_status_schema_handler(fail_status, 1)
    )
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with patch("apicurio_serdes._client.time.sleep"):
        result = client.get_schema("UserEvent")
    assert result.schema == USER_EVENT_SCHEMA_JSON


# No retry on non-retryable errors


def test_get_schema_no_retry_on_404(mock_registry: respx.MockRouter) -> None:
    """404 raises SchemaNotFoundError immediately — no retry."""
    from apicurio_serdes._errors import SchemaNotFoundError

    url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/Missing/versions/latest/content"
    route = mock_registry.get(url).mock(return_value=httpx.Response(404, json={}))
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(SchemaNotFoundError):
        client.get_schema("Missing")
    assert route.call_count == 1


def test_get_schema_no_retry_on_400(mock_registry: respx.MockRouter) -> None:
    """400 raises RegistryConnectionError immediately — no retry."""
    from apicurio_serdes._errors import RegistryConnectionError

    url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/Bad/versions/latest/content"
    route = mock_registry.get(url).mock(return_value=httpx.Response(400))
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(RegistryConnectionError):
        client.get_schema("Bad")
    assert route.call_count == 1


def test_get_schema_no_retry_on_500(mock_registry: respx.MockRouter) -> None:
    """500 raises RegistryConnectionError immediately — not retried (ambiguous)."""
    from apicurio_serdes._errors import RegistryConnectionError

    url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/Broken/versions/latest/content"
    route = mock_registry.get(url).mock(return_value=httpx.Response(500))
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(RegistryConnectionError):
        client.get_schema("Broken")
    assert route.call_count == 1


def test_get_schema_max_retries_zero_no_retry(
    mock_registry: respx.MockRouter,
) -> None:
    """max_retries=0 disables retry; ConnectError raises immediately after 1 attempt."""
    from apicurio_serdes._errors import RegistryConnectionError

    url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/UserEvent/versions/latest/content"
    route = mock_registry.get(url).mock(side_effect=httpx.ConnectError("refused"))
    client = ApicurioRegistryClient(
        url=REGISTRY_URL, group_id=GROUP_ID, max_retries=0
    )
    with pytest.raises(RegistryConnectionError):
        client.get_schema("UserEvent")
    assert route.call_count == 1


def test_get_schema_exhausts_retries_on_503_raises_connection_error(
    mock_registry: respx.MockRouter,
) -> None:
    """When all retries on 503 are exhausted, RegistryConnectionError is raised."""
    from apicurio_serdes._errors import RegistryConnectionError

    url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/UserEvent/versions/latest/content"
    mock_registry.get(url).mock(return_value=httpx.Response(503))
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID, max_retries=1)
    with patch("apicurio_serdes._client.time.sleep"):
        with pytest.raises(RegistryConnectionError):
            client.get_schema("UserEvent")


# Backoff


def test_get_schema_sleep_called_between_retries(
    mock_registry: respx.MockRouter,
) -> None:
    """time.sleep is called with a positive delay between retry attempts."""
    url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/UserEvent/versions/latest/content"
    mock_registry.get(url).mock(side_effect=_flaky_schema_handler(1))
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with patch("apicurio_serdes._client.time.sleep") as mock_sleep:
        client.get_schema("UserEvent")
    mock_sleep.assert_called_once()
    delay = mock_sleep.call_args[0][0]
    assert delay >= 0


# Escape hatch: custom http_client


def test_custom_http_client_is_used() -> None:
    """User-provided http_client is used for HTTP requests."""
    mock_client = MagicMock(spec=httpx.Client)
    _req = httpx.Request("GET", f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/UserEvent/versions/latest/content")
    mock_client.request.return_value = httpx.Response(
        200,
        content=json.dumps(USER_EVENT_SCHEMA_JSON).encode(),
        headers={
            "X-Registry-GlobalId": str(GLOBAL_ID),
            "X-Registry-ContentId": str(CONTENT_ID),
        },
        request=_req,
    )
    client = ApicurioRegistryClient(
        url=REGISTRY_URL, group_id=GROUP_ID, http_client=mock_client
    )
    result = client.get_schema("UserEvent")
    assert result.schema == USER_EVENT_SCHEMA_JSON
    assert mock_client.request.called


def test_custom_http_client_not_closed_on_close() -> None:
    """User-provided http_client is not closed when client.close() is called."""
    mock_client = MagicMock(spec=httpx.Client)
    client = ApicurioRegistryClient(
        url=REGISTRY_URL, group_id=GROUP_ID, http_client=mock_client
    )
    client.close()
    mock_client.close.assert_not_called()
