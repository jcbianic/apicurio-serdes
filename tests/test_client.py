"""Step definitions for TS-008, TS-010, TS-011, TS-012: ApicurioRegistryClient scenarios."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
import respx
from pytest_bdd import given, parsers, scenario, then, when

from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroSerializer
from apicurio_serdes.serialization import MessageField, SerializationContext
import httpx

from tests.conftest import (
    GROUP_ID,
    REGISTRY_URL,
    USER_EVENT_SCHEMA_JSON,
    VALID_USER_EVENT,
    VALID_USER_EVENT_ALT,
    _id_not_found_route,
    _id_schema_route,
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
    from apicurio_serdes._errors import RegistryConnectionError
    from httpx import Response

    url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/Broken/versions/latest/content"
    mock_registry.get(url).mock(return_value=Response(500))
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    with pytest.raises(RegistryConnectionError):
        client.get_schema("Broken")


def test_get_schema_by_global_id_500_raises_registry_connection_error(
    mock_registry: respx.MockRouter,
) -> None:
    """Unexpected HTTP status in _get_schema_by_id raises RegistryConnectionError [FR-013]."""
    from apicurio_serdes._errors import RegistryConnectionError
    from httpx import Response

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

    mock_registry.get(
        url__startswith=f"{REGISTRY_URL}/ids/globalIds/"
    ).mock(side_effect=httpx.ConnectError("refused"))
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

    mock_registry.get(
        url__startswith=f"{REGISTRY_URL}/ids/contentIds/"
    ).mock(side_effect=httpx.ConnectError("refused"))
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
