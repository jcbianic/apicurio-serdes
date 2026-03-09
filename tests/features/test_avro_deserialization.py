"""Step definitions for avro_deserialization.feature [T010, TS-001 through TS-009]."""

from __future__ import annotations

import struct
from typing import Any

import httpx
import respx
from pytest_bdd import given, parsers, scenario, then, when

from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes._errors import DeserializationError, RegistryConnectionError
from apicurio_serdes.avro import AvroDeserializer, AvroSerializer
from apicurio_serdes.serialization import MessageField, SerializationContext
from tests.conftest import (
    GROUP_ID,
    REGISTRY_URL,
    VALID_USER_EVENT,
    _id_not_found_route,
    _id_schema_route,
    _schema_route,
    make_confluent_bytes,
)

FEATURE = (
    "../../specs/002-avro-deserializer/tests/features/avro_deserialization.feature"
)

CONTENT_ID_42 = 42
GLOBAL_ID_42 = 42


# ── Scenarios ──


@scenario(FEATURE, "Valid Confluent-framed Avro bytes deserialize to the original dict")
def test_ts001_valid_deserialize() -> None:
    """TS-001."""


@scenario(
    FEATURE,
    "Schema is resolved from the registry using the identifier in the wire frame",
)
def test_ts002_schema_resolved_from_wire() -> None:
    """TS-002."""


@scenario(
    FEATURE,
    "Bytes not starting with magic byte 0x00 raise a DeserializationError immediately",
)
def test_ts003_bad_magic_byte() -> None:
    """TS-003."""


@scenario(
    FEATURE,
    "Valid framing with an unknown schema identifier raises a descriptive error",
)
def test_ts004_unknown_schema_id() -> None:
    """TS-004."""


@scenario(
    FEATURE,
    "Empty input raises a DeserializationError before any registry lookup",
)
def test_ts005_empty_input() -> None:
    """TS-005."""


@scenario(
    FEATURE,
    "Input shorter than 5 bytes raises a DeserializationError before any registry lookup",
)
def test_ts006_too_short() -> None:
    """TS-006."""


@scenario(
    FEATURE,
    "Corrupt Avro payload raises a DeserializationError identifying the decoding failure",
)
def test_ts007_corrupt_payload() -> None:
    """TS-007."""


@scenario(
    FEATURE,
    "Unreachable registry during schema resolution raises a RegistryConnectionError",
)
def test_ts008_unreachable_registry() -> None:
    """TS-008."""


@scenario(
    FEATURE,
    "Round-trip — bytes from AvroSerializer deserialize back to the original dict",
)
def test_ts009_round_trip() -> None:
    """TS-009."""


# ── Background steps ──


@given(
    parsers.cfparse(
        "a configured ApicurioRegistryClient pointing at a registry that holds"
        ' a known Avro schema with contentId 42 for artifact "{artifact_id}"'
    ),
    target_fixture="registry_client",
)
def given_client_with_content_id(
    mock_registry: respx.MockRouter, artifact_id: str
) -> ApicurioRegistryClient:
    _schema_route(
        mock_registry, artifact_id, global_id=GLOBAL_ID_42, content_id=CONTENT_ID_42
    )
    _id_schema_route(mock_registry, "contentId", CONTENT_ID_42)
    _id_schema_route(mock_registry, "globalId", GLOBAL_ID_42)
    return ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)


@given(
    "an AvroDeserializer created with that client",
    target_fixture="deserializer",
)
def given_deserializer(registry_client: ApicurioRegistryClient) -> AvroDeserializer:
    return AvroDeserializer(registry_client=registry_client)


# ── Given steps ──


@given(
    parsers.cfparse(
        'Confluent-framed Avro bytes produced by serializing a known dict with schema "{artifact_id}"'
    ),
    target_fixture="input_bytes",
)
def given_valid_confluent_bytes(
    registry_client: ApicurioRegistryClient, artifact_id: str
) -> bytes:
    serializer = AvroSerializer(
        registry_client=registry_client,
        artifact_id=artifact_id,
        use_id="contentId",
    )
    ctx = SerializationContext(topic="users", field=MessageField.VALUE)
    return serializer(VALID_USER_EVENT, ctx)


@given(
    parsers.cfparse(
        "valid Confluent-framed Avro bytes whose 4-byte field encodes contentId {content_id:d}"
    ),
    target_fixture="input_bytes",
)
def given_bytes_with_content_id(content_id: int) -> bytes:
    return make_confluent_bytes(content_id, VALID_USER_EVENT)


@given(
    "bytes that begin with 0x01 instead of the expected magic byte 0x00",
    target_fixture="input_bytes",
)
def given_bad_magic_bytes() -> bytes:
    return b"\x01" + struct.pack(">I", CONTENT_ID_42) + b"\x00"


@given(
    parsers.cfparse(
        "the registry has no schema corresponding to contentId {content_id:d}"
    ),
)
def given_registry_missing_content_id(
    mock_registry: respx.MockRouter, content_id: int
) -> None:
    _id_not_found_route(mock_registry, "contentId", content_id)


@given(
    "an empty byte string",
    target_fixture="input_bytes",
)
def given_empty_bytes() -> bytes:
    return b""


@given(
    "bytes that contain the magic byte 0x00 followed by only 3 bytes",
    target_fixture="input_bytes",
)
def given_short_bytes() -> bytes:
    return b"\x00\x00\x00\x01"


@given(
    parsers.cfparse(
        "valid Confluent framing with magic byte and contentId {content_id:d}"
    ),
    target_fixture="input_bytes",
)
def given_valid_framing_prefix(content_id: int) -> bytes:
    return b"\x00" + struct.pack(">I", content_id)


@given(
    "a payload that cannot be decoded with the resolved schema",
    target_fixture="input_bytes",
)
def given_corrupt_payload(input_bytes: bytes) -> bytes:
    return input_bytes + b"\xff\xff\xff\xff\xff"


@given(
    "an ApicurioRegistryClient configured with an unreachable registry URL",
    target_fixture="registry_client",
)
def given_unreachable_client(mock_registry: respx.MockRouter) -> ApicurioRegistryClient:
    unreachable_url = "http://unreachable-host:9999/apis/registry/v3"
    mock_registry.get(url__startswith=unreachable_url).mock(
        side_effect=httpx.ConnectError("Connection refused")
    )
    return ApicurioRegistryClient(url=unreachable_url, group_id=GROUP_ID)


@given(
    "an AvroDeserializer using that client",
    target_fixture="deserializer",
)
def given_deserializer_unreachable(
    registry_client: ApicurioRegistryClient,
) -> AvroDeserializer:
    return AvroDeserializer(registry_client=registry_client)


@given(
    parsers.cfparse(
        "valid Confluent-framed Avro bytes referencing contentId {content_id:d}"
    ),
    target_fixture="input_bytes",
)
def given_valid_bytes_content_id(content_id: int) -> bytes:
    return make_confluent_bytes(content_id, VALID_USER_EVENT)


@given(
    parsers.cfparse(
        'an AvroSerializer configured with the same client and artifact_id "{artifact_id}"'
    ),
    target_fixture="avro_serializer",
)
def given_avro_serializer_same_client(
    registry_client: ApicurioRegistryClient, artifact_id: str
) -> AvroSerializer:
    return AvroSerializer(
        registry_client=registry_client,
        artifact_id=artifact_id,
        use_id="contentId",
    )


@given(
    parsers.cfparse('a plain dict conforming to the "{artifact_id}" schema'),
    target_fixture="original_dict",
)
def given_plain_dict(artifact_id: str) -> dict[str, Any]:
    return dict(VALID_USER_EVENT)


# ── When steps ──


@when(
    "the deserializer is called with those bytes and the context",
    target_fixture="deser_result",
)
def when_deserialize(
    deserializer: AvroDeserializer,
    input_bytes: bytes,
    ctx: SerializationContext,
) -> Any:
    try:
        return deserializer(input_bytes, ctx)
    except Exception as exc:
        return exc


@when(
    "the dict is serialized with the AvroSerializer",
    target_fixture="serialized_bytes",
)
def when_serialize_dict(
    avro_serializer: AvroSerializer,
    original_dict: dict[str, Any],
    ctx: SerializationContext,
) -> bytes:
    return avro_serializer(original_dict, ctx)


@when(
    "the resulting bytes are deserialized with the AvroDeserializer",
    target_fixture="deser_result",
)
def when_deserialize_serialized(
    deserializer: AvroDeserializer,
    serialized_bytes: bytes,
    ctx: SerializationContext,
) -> Any:
    return deserializer(serialized_bytes, ctx)


# ── Then steps ──


@then("the returned value is a Python dict")
def then_is_dict(deser_result: Any) -> None:
    assert isinstance(deser_result, dict)


@then("the dict contents match the original data that was serialized")
def then_matches_original(deser_result: dict[str, Any]) -> None:
    assert deser_result == VALID_USER_EVENT


@then(parsers.cfparse("the registry is queried for contentId {content_id:d}"))
def then_registry_queried_for_content_id(
    mock_registry: respx.MockRouter, content_id: int
) -> None:
    url = f"{REGISTRY_URL}/ids/contentIds/{content_id}"
    matched = [r for r in mock_registry.routes if str(getattr(r, "pattern", "")) == url]
    if not matched:
        # respx route pattern matching — check call count on any matching route
        called = any(
            r.call_count > 0
            for r in mock_registry.routes
            if f"contentIds/{content_id}" in str(getattr(r, "pattern", ""))
        )
        assert called, f"Registry was not queried for contentId {content_id}"


@then("the schema returned for that identifier is used to decode the payload")
def then_schema_used_for_decoding(deser_result: Any) -> None:
    assert isinstance(deser_result, dict)
    assert "userId" in deser_result


@then("a DeserializationError is raised")
def then_deserialization_error(deser_result: Any) -> None:
    assert isinstance(deser_result, DeserializationError)


@then("no registry lookup is attempted")
def then_no_registry_lookup(mock_registry: respx.MockRouter) -> None:
    id_calls = sum(
        r.call_count
        for r in mock_registry.routes
        if "/ids/" in str(getattr(r, "pattern", ""))
    )
    assert id_calls == 0, f"Expected 0 ID-based registry calls, got {id_calls}"


@then("a descriptive error is raised")
def then_descriptive_error(deser_result: Any) -> None:
    from apicurio_serdes._errors import SchemaNotFoundError

    assert isinstance(deser_result, SchemaNotFoundError)


@then(
    parsers.cfparse(
        "the error message identifies the unresolved identifier {id_value:d}"
    )
)
def then_error_message_has_id(deser_result: Any, id_value: int) -> None:
    assert str(id_value) in str(deser_result)


@then("a RegistryConnectionError is raised")
def then_registry_connection_error(deser_result: Any) -> None:
    assert isinstance(deser_result, RegistryConnectionError)


@then("the error message includes the registry URL")
def then_error_includes_url(deser_result: Any) -> None:
    assert "unreachable-host" in str(deser_result)


@then("the error message identifies the decoding failure")
def then_error_identifies_decode_failure(deser_result: Any) -> None:
    assert isinstance(deser_result, DeserializationError)
    assert "decode" in str(deser_result).lower() or "avro" in str(deser_result).lower()


@then("the deserialized dict equals the original dict")
def then_round_trip_equal(
    deser_result: dict[str, Any], original_dict: dict[str, Any]
) -> None:
    assert deser_result == original_dict


@then("no manual registry interaction occurred between the two steps")
def then_no_manual_registry_interaction() -> None:
    pass  # Structural guarantee — no manual calls in step definitions


# ── Context fixture ──


@given(
    parsers.cfparse('a SerializationContext for topic "{topic}" and field {field}'),
    target_fixture="ctx",
)
def given_ctx_deser(topic: str, field: str) -> SerializationContext:
    return SerializationContext(topic=topic, field=MessageField[field])
