"""Step definitions for TS-016, TS-017, TS-018: Wire format scenarios."""

from __future__ import annotations

import struct
from typing import Any

import respx
from pytest_bdd import given, parsers, scenario, then, when

from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroSerializer
from apicurio_serdes.serialization import (
    MessageField,
    SerializationContext,
    SerializedMessage,
    WireFormat,
)
from tests.conftest import (
    CONTENT_ID,
    GLOBAL_ID,
    GROUP_ID,
    REGISTRY_URL,
    VALID_USER_EVENT,
    _schema_route,
)

FEATURE = "../specs/001-avro-serializer/tests/features/wire_format.feature"


# ── Scenarios ──


@scenario(
    FEATURE, "Default wire format embeds globalId as the 4-byte schema identifier"
)
def test_ts016_global_id_wire_format() -> None:
    """TS-016."""


@scenario(FEATURE, "Wire format embeds contentId when use_id is set to contentId")
def test_ts017_content_id_wire_format() -> None:
    """TS-017."""


@scenario(
    FEATURE,
    "AvroSerializer callable interface mirrors the confluent-kafka serializer convention",
)
def test_ts018_callable_interface() -> None:
    """TS-018."""


@given(
    parsers.cfparse('a valid dict conforming to the "{artifact_id}" schema'),
    target_fixture="valid_dict",
)
def given_valid_dict(artifact_id: str) -> dict[str, Any]:
    return VALID_USER_EVENT


@given(
    parsers.cfparse('a SerializationContext for topic "{topic}" and field {field}'),
    target_fixture="ctx",
)
def given_ctx(topic: str, field: str) -> SerializationContext:
    return SerializationContext(topic=topic, field=MessageField[field])


# ── Given steps for specific scenarios ──


@given(
    parsers.cfparse(
        'an AvroSerializer configured with use_id="{use_id}" and artifact_id "{artifact_id}"'
    ),
    target_fixture="serializer",
)
def given_serializer_with_use_id(
    registry_client: ApicurioRegistryClient, use_id: str, artifact_id: str
) -> AvroSerializer:
    return AvroSerializer(
        registry_client=registry_client,
        artifact_id=artifact_id,
        use_id=use_id,  # type: ignore[arg-type]
    )


@given(
    parsers.cfparse('an AvroSerializer instance bound to artifact_id "{artifact_id}"'),
    target_fixture="serializer",
)
def given_serializer_bound(
    registry_client: ApicurioRegistryClient, artifact_id: str
) -> AvroSerializer:
    return AvroSerializer(registry_client=registry_client, artifact_id=artifact_id)


# ── When steps ──


@when(
    "the serializer is called with the valid dict",
    target_fixture="result_bytes",
)
def when_call_serializer(
    serializer: AvroSerializer, valid_dict: dict[str, Any], ctx: SerializationContext
) -> bytes:
    return serializer(valid_dict, ctx)


@when(
    parsers.cfparse(
        "the serializer is called as serializer(data, ctx) with a valid dict and SerializationContext"
    ),
    target_fixture="result_bytes",
)
def when_call_as_callable(
    serializer: AvroSerializer, valid_dict: dict[str, Any], ctx: SerializationContext
) -> bytes:
    return serializer(valid_dict, ctx)


# ── Then steps ──


@then(parsers.cfparse("output byte 0 is 0x00"))
def then_magic_byte(result_bytes: bytes) -> None:
    assert result_bytes[0:1] == b"\x00"


@then(
    parsers.cfparse(
        "bytes 1 through 4 contain the value {expected_id:d} encoded as a big-endian unsigned 32-bit integer"
    )
)
def then_id_bytes(result_bytes: bytes, expected_id: int) -> None:
    actual_id = struct.unpack(">I", result_bytes[1:5])[0]
    assert actual_id == expected_id


@then("the return value is of type bytes")
def then_is_bytes(result_bytes: bytes) -> None:
    assert isinstance(result_bytes, bytes)


@then("the return value begins with magic byte 0x00")
def then_begins_with_magic(result_bytes: bytes) -> None:
    assert result_bytes[0:1] == b"\x00"


# ── KAFKA_HEADERS byte-level unit tests ──


def _serialize_kafka_headers(
    mock_registry: respx.MockRouter,
    *,
    use_id: str = "globalId",
    field: MessageField = MessageField.VALUE,
) -> SerializedMessage:
    """Helper: serialize VALID_USER_EVENT with KAFKA_HEADERS wire format."""
    _schema_route(mock_registry, "UserEvent")
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    serializer = AvroSerializer(
        registry_client=client,
        artifact_id="UserEvent",
        use_id=use_id,  # type: ignore[arg-type]
        wire_format=WireFormat.KAFKA_HEADERS,
    )
    ctx = SerializationContext(topic="test-topic", field=field)
    return serializer.serialize(VALID_USER_EVENT, ctx)


def test_kafka_headers_header_name_value_global_id(
    mock_registry: respx.MockRouter,
) -> None:
    """KAFKA_HEADERS with field=VALUE, use_id=globalId produces header key 'apicurio.value.globalId'."""
    result = _serialize_kafka_headers(
        mock_registry, use_id="globalId", field=MessageField.VALUE
    )
    assert "apicurio.value.globalId" in result.headers


def test_kafka_headers_header_name_value_content_id(
    mock_registry: respx.MockRouter,
) -> None:
    """KAFKA_HEADERS with field=VALUE, use_id=contentId produces header key 'apicurio.value.contentId'."""
    result = _serialize_kafka_headers(
        mock_registry, use_id="contentId", field=MessageField.VALUE
    )
    assert "apicurio.value.contentId" in result.headers


def test_kafka_headers_header_name_key_global_id(
    mock_registry: respx.MockRouter,
) -> None:
    """KAFKA_HEADERS with field=KEY, use_id=globalId produces header key 'apicurio.key.globalId'."""
    result = _serialize_kafka_headers(
        mock_registry, use_id="globalId", field=MessageField.KEY
    )
    assert "apicurio.key.globalId" in result.headers


def test_kafka_headers_header_name_key_content_id(
    mock_registry: respx.MockRouter,
) -> None:
    """KAFKA_HEADERS with field=KEY, use_id=contentId produces header key 'apicurio.key.contentId'."""
    result = _serialize_kafka_headers(
        mock_registry, use_id="contentId", field=MessageField.KEY
    )
    assert "apicurio.key.contentId" in result.headers


def test_kafka_headers_header_value_8byte_big_endian(
    mock_registry: respx.MockRouter,
) -> None:
    """KAFKA_HEADERS encodes globalId as 8-byte big-endian signed long."""
    result = _serialize_kafka_headers(
        mock_registry, use_id="globalId", field=MessageField.VALUE
    )
    value = result.headers["apicurio.value.globalId"]
    assert len(value) == 8
    assert struct.unpack(">q", value)[0] == GLOBAL_ID


def test_kafka_headers_header_value_content_id_encoding(
    mock_registry: respx.MockRouter,
) -> None:
    """KAFKA_HEADERS encodes contentId as 8-byte big-endian signed long."""
    result = _serialize_kafka_headers(
        mock_registry, use_id="contentId", field=MessageField.VALUE
    )
    value = result.headers["apicurio.value.contentId"]
    assert len(value) == 8
    assert struct.unpack(">q", value)[0] == CONTENT_ID


def test_kafka_headers_payload_no_magic_byte(
    mock_registry: respx.MockRouter,
) -> None:
    """KAFKA_HEADERS payload does not start with the confluent magic byte 0x00."""
    result = _serialize_kafka_headers(mock_registry)
    assert len(result.payload) > 0
    assert result.payload[0:1] != b"\x00"


def test_kafka_headers_exactly_one_header(
    mock_registry: respx.MockRouter,
) -> None:
    """KAFKA_HEADERS produces exactly one header entry."""
    result = _serialize_kafka_headers(mock_registry)
    assert len(result.headers) == 1
