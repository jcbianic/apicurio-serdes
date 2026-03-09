"""Step definitions for schema_caching.feature [T016, T017, TS-010, TS-011, TS-012]."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

import respx
from pytest_bdd import given, parsers, scenario, then, when

from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroDeserializer
from apicurio_serdes.serialization import MessageField, SerializationContext
from tests.conftest import (
    GROUP_ID,
    REGISTRY_URL,
    USER_EVENT_SCHEMA_JSON,
    VALID_USER_EVENT,
    _id_schema_route,
    make_confluent_bytes,
)

FEATURE = "../../specs/002-avro-deserializer/tests/features/schema_caching.feature"

SCHEMA_A_CONTENT_ID = 42
SCHEMA_B_CONTENT_ID = 43

SCHEMA_B_JSON: dict[str, Any] = {
    "type": "record",
    "name": "SchemaB",
    "namespace": "com.example",
    "fields": [{"name": "id", "type": "string"}],
}


# ── Scenarios ──


@scenario(
    FEATURE,
    "Registry is contacted exactly once when the same schema identifier is deserialized multiple times",
)
def test_ts010_cache_single_schema() -> None:
    """TS-010."""


@scenario(
    FEATURE,
    "A new schema identifier triggers one registry call without re-fetching a previously cached schema",
)
def test_ts011_cache_multiple_schemas() -> None:
    """TS-011."""


@scenario(
    FEATURE,
    "Concurrent deserialization of the same schema identifier results in exactly one registry HTTP request",
)
def test_ts012_concurrent_cache() -> None:
    """TS-012."""


# ── Background steps ──


@given(
    parsers.cfparse(
        "a configured ApicurioRegistryClient pointing at a registry that holds"
        ' schemas with contentId {id_a:d} ("{art_a}") and contentId {id_b:d} ("{art_b}")'
    ),
    target_fixture="registry_client",
)
def given_client_with_two_schemas(
    mock_registry: respx.MockRouter, id_a: int, art_a: str, id_b: int, art_b: str
) -> ApicurioRegistryClient:
    _id_schema_route(mock_registry, "contentId", id_a, schema=USER_EVENT_SCHEMA_JSON)
    _id_schema_route(mock_registry, "contentId", id_b, schema=SCHEMA_B_JSON)
    return ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)


# ── Given steps ──


@given(
    "an AvroDeserializer configured with the client",
    target_fixture="deserializer",
)
def given_deserializer_with_client(
    registry_client: ApicurioRegistryClient,
) -> AvroDeserializer:
    return AvroDeserializer(registry_client=registry_client)


@given(
    parsers.cfparse(
        "a message referencing contentId {content_id:d} has already been deserialized"
        " and contentId {content_id2:d} is cached"
    ),
)
def given_message_already_deserialized(
    deserializer: AvroDeserializer, content_id: int, content_id2: int
) -> None:
    ctx = SerializationContext(topic="warmup", field=MessageField.VALUE)
    msg = make_confluent_bytes(content_id, VALID_USER_EVENT)
    deserializer(msg, ctx)


@given(
    parsers.cfparse(
        "an ApicurioRegistryClient pointing at a registry that holds"
        " a schema with contentId {content_id:d}"
    ),
    target_fixture="registry_client",
)
def given_client_with_single_schema(
    mock_registry: respx.MockRouter, content_id: int
) -> ApicurioRegistryClient:
    _id_schema_route(mock_registry, "contentId", content_id)
    return ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)


@given(
    "an AvroDeserializer configured with that client",
    target_fixture="deserializer",
)
def given_deserializer_with_that_client(
    registry_client: ApicurioRegistryClient,
) -> AvroDeserializer:
    return AvroDeserializer(registry_client=registry_client)


# ── When steps ──


@when(
    parsers.cfparse(
        "{count:d} Confluent-framed messages all referencing contentId {content_id:d}"
        " are deserialized in sequence"
    ),
    target_fixture="sequence_results",
)
def when_deserialize_many_sequence(
    deserializer: AvroDeserializer, count: int, content_id: int
) -> list[Any]:
    ctx = SerializationContext(topic="events", field=MessageField.VALUE)
    msg = make_confluent_bytes(content_id, VALID_USER_EVENT)
    return [deserializer(msg, ctx) for _ in range(count)]


@when(
    parsers.cfparse(
        "a message referencing contentId {content_id:d} is deserialized for the first time"
    ),
    target_fixture="new_result",
)
def when_deserialize_new_schema(deserializer: AvroDeserializer, content_id: int) -> Any:
    ctx = SerializationContext(topic="events", field=MessageField.VALUE)
    msg = make_confluent_bytes(content_id, {"id": "test-123"}, schema=SCHEMA_B_JSON)
    return deserializer(msg, ctx)


@when(
    "many messages all referencing contentId 42 are deserialized concurrently from multiple threads",
    target_fixture="concurrent_results",
)
def when_deserialize_concurrent(deserializer: AvroDeserializer) -> list[Any]:
    ctx = SerializationContext(topic="concurrent", field=MessageField.VALUE)
    msg = make_confluent_bytes(SCHEMA_A_CONTENT_ID, VALID_USER_EVENT)

    def _deser(_: int) -> Any:
        return deserializer(msg, ctx)

    with ThreadPoolExecutor(max_workers=20) as pool:
        return list(pool.map(_deser, range(20)))


# ── Then steps ──


@then(
    parsers.cfparse(
        "the registry is contacted exactly once for contentId {content_id:d}"
    )
)
def then_contacted_once_for_content_id(
    mock_registry: respx.MockRouter, content_id: int
) -> None:
    route_calls = sum(
        r.call_count
        for r in mock_registry.routes
        if f"contentIds/{content_id}" in str(getattr(r, "pattern", ""))
    )
    assert route_calls == 1, (
        f"Expected 1 call for contentId {content_id}, got {route_calls}"
    )


@then(
    parsers.cfparse("the registry is not contacted again for contentId {content_id:d}")
)
def then_not_contacted_again_for_content_id(
    mock_registry: respx.MockRouter, content_id: int
) -> None:
    route_calls = sum(
        r.call_count
        for r in mock_registry.routes
        if f"contentIds/{content_id}" in str(getattr(r, "pattern", ""))
    )
    assert route_calls == 1, (
        f"Expected contentId {content_id} to be fetched only once, got {route_calls}"
    )


@then("all deserialized results are correct Python dicts")
def then_all_results_are_dicts(concurrent_results: list[Any]) -> None:
    for result in concurrent_results:
        assert isinstance(result, dict)
        assert result == VALID_USER_EVENT
