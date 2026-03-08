"""Step definitions for KAFKA_HEADERS serialization scenarios [TS-001..TS-008].

Tests the KAFKA_HEADERS wire format branch of AvroSerializer.serialize().
The production code is already implemented; these BDD tests verify end-to-end
behavior including payload format, header naming, error handling, and caching.
"""

from __future__ import annotations

import io
import struct
from typing import Any

import fastavro
import pytest
import respx
from pytest_bdd import given, parsers, scenario, then, when

from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes._errors import SchemaNotFoundError
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
    INVALID_USER_EVENT_MISSING_FIELD,
    REGISTRY_URL,
    USER_EVENT_SCHEMA_JSON,
    VALID_USER_EVENT,
    _not_found_route,
    _schema_route,
)

FEATURES_BASE = "../../specs/004-kafka-headers-wire-format/tests/features"
FEATURE = f"{FEATURES_BASE}/kafka_headers_serialization.feature"


# ── Default fixtures ──


@pytest.fixture()
def ctx() -> SerializationContext:
    """Default serialization context (VALUE field).

    Overridden by the 'the SerializationContext field is' Given step
    when a scenario needs a non-default field.
    """
    return SerializationContext(topic="test-topic", field=MessageField.VALUE)


# ── Scenarios ──


@scenario(FEATURE, "Payload contains no framing bytes in KAFKA_HEADERS mode")
def test_ts001_payload_no_framing_bytes() -> None:
    """TS-001."""


@scenario(
    FEATURE,
    "Schema identifier header uses Apicurio native naming convention",
)
def test_ts002_header_naming() -> None:
    """TS-002: Scenario Outline parametrized across 4 example rows."""


@scenario(
    FEATURE,
    "Error raised for invalid data before any bytes or headers produced",
)
def test_ts003_error_for_invalid_data() -> None:
    """TS-003."""


@scenario(
    FEATURE,
    "KAFKA_HEADERS payload decodes correctly when schema is taken from headers",
)
def test_ts004_payload_decodes_correctly() -> None:
    """TS-004."""


@scenario(FEATURE, "Header value is encoded as 8-byte big-endian signed long")
def test_ts005_header_value_encoding() -> None:
    """TS-005."""


@scenario(
    FEATURE,
    "use_id=contentId places the content identifier in the header for KAFKA_HEADERS mode",
)
def test_ts006_content_id_in_header() -> None:
    """TS-006."""


@scenario(
    FEATURE,
    "SchemaNotFoundError raised when artifact is missing \u2014 no bytes or headers returned",
)
def test_ts007_schema_not_found_error() -> None:
    """TS-007."""


@scenario(
    FEATURE,
    "Schema caching preserved \u2014 1000 consecutive serializations use exactly 1 HTTP call",
)
def test_ts008_schema_caching() -> None:
    """TS-008."""


# ── Background / Given steps ──


@given(
    "an AvroSerializer configured with WireFormat.KAFKA_HEADERS",
    target_fixture="serializer",
)
def given_kafka_headers_serializer(
    mock_registry: respx.MockRouter,
) -> AvroSerializer:
    """Background step: create a default KAFKA_HEADERS serializer."""
    _schema_route(mock_registry, "UserEvent")
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    return AvroSerializer(
        registry_client=client,
        artifact_id="UserEvent",
        wire_format=WireFormat.KAFKA_HEADERS,
    )


@given("a schema artifact exists in the registry")
def given_schema_artifact_exists() -> None:
    """Schema route already registered in the background step."""


@given(
    parsers.cfparse('the AvroSerializer is configured with use_id "{use_id}"'),
    target_fixture="serializer",
)
def given_serializer_with_use_id(
    mock_registry: respx.MockRouter, use_id: str
) -> AvroSerializer:
    """Reconfigure serializer with a specific use_id."""
    _schema_route(mock_registry, "UserEvent")
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    return AvroSerializer(
        registry_client=client,
        artifact_id="UserEvent",
        use_id=use_id,
        wire_format=WireFormat.KAFKA_HEADERS,
    )


@given(
    parsers.cfparse('the SerializationContext field is "{field}"'),
    target_fixture="ctx",
)
def given_serialization_context_field(field: str) -> SerializationContext:
    """Create a SerializationContext with the specified field."""
    message_field = MessageField.KEY if field == "KEY" else MessageField.VALUE
    return SerializationContext(topic="test-topic", field=message_field)


@given(
    "no schema artifact exists in the registry for the configured artifact ID",
    target_fixture="serializer",
)
def given_no_schema_artifact(mock_registry: respx.MockRouter) -> AvroSerializer:
    """Configure a serializer pointing at a non-existent artifact."""
    _not_found_route(mock_registry, "MissingArtifact")
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    return AvroSerializer(
        registry_client=client,
        artifact_id="MissingArtifact",
        wire_format=WireFormat.KAFKA_HEADERS,
    )


# ── When steps ──


@when(
    "the serialize() method is called with a valid dict and a SerializationContext",
    target_fixture="serialize_result",
)
def when_serialize_valid_dict(
    serializer: AvroSerializer,
    ctx: SerializationContext,
) -> dict[str, Any]:
    """Call serialize() with VALID_USER_EVENT, capturing any exception.

    Stores both the SerializedMessage (on success) and the exception (on failure)
    so that Then steps for both success (TS-001..TS-006) and error (TS-007)
    scenarios can inspect the result.
    """
    result: dict[str, Any] = {"message": None, "error": None}
    try:
        result["message"] = serializer.serialize(VALID_USER_EVENT, ctx)
    except Exception as exc:
        result["error"] = exc
    return result


@when(
    "the serialize() method is called with a dict that is missing a required schema field",
    target_fixture="serialize_error_result",
)
def when_serialize_invalid_dict(
    serializer: AvroSerializer,
) -> dict[str, Any]:
    """Call serialize() with invalid data and capture exception."""
    ctx = SerializationContext(topic="test-topic", field=MessageField.VALUE)
    result: dict[str, Any] = {"error": None, "message": None}
    try:
        msg = serializer.serialize(INVALID_USER_EVENT_MISSING_FIELD, ctx)
        result["message"] = msg
    except Exception as exc:
        result["error"] = exc
    return result


@when(
    "the raw payload bytes are decoded by an Avro binary reader using the schema from the registry",
    target_fixture="decoded_record",
)
def when_decode_payload(serialize_result: dict[str, Any]) -> dict[str, Any]:
    """Decode the raw Avro payload using fastavro and the known schema."""
    msg: SerializedMessage = serialize_result["message"]
    parsed_schema = fastavro.parse_schema(USER_EVENT_SCHEMA_JSON)
    reader = io.BytesIO(msg.payload)
    return fastavro.schemaless_reader(reader, parsed_schema)


@when(
    "the serialize() method is called 1000 consecutive times with the same artifact",
    target_fixture="serialize_result",
)
def when_serialize_1000_times(
    serializer: AvroSerializer,
) -> dict[str, Any]:
    """Call serialize() 1000 times. Return the last result."""
    ctx = SerializationContext(topic="test-topic", field=MessageField.VALUE)
    last_msg = None
    for _ in range(1000):
        last_msg = serializer.serialize(VALID_USER_EVENT, ctx)
    return {"message": last_msg, "error": None}


# ── Then steps ──


@then("the returned payload contains only raw Avro binary")
def then_payload_is_raw_avro(serialize_result: dict[str, Any]) -> None:
    """Verify the payload can be decoded as raw Avro (no framing prefix)."""
    msg: SerializedMessage = serialize_result["message"]
    parsed_schema = fastavro.parse_schema(USER_EVENT_SCHEMA_JSON)
    reader = io.BytesIO(msg.payload)
    record = fastavro.schemaless_reader(reader, parsed_schema)
    assert record == VALID_USER_EVENT


@then("the returned payload does not begin with magic byte 0x00")
def then_no_magic_byte(serialize_result: dict[str, Any]) -> None:
    msg: SerializedMessage = serialize_result["message"]
    assert msg.payload[0:1] != b"\x00"


@then("the returned payload does not contain a 4-byte schema identifier prefix")
def then_no_4byte_prefix(serialize_result: dict[str, Any]) -> None:
    """Verify payload is exactly the raw Avro-encoded bytes (no Confluent framing)."""
    msg: SerializedMessage = serialize_result["message"]
    parsed_schema = fastavro.parse_schema(USER_EVENT_SCHEMA_JSON)
    buf = io.BytesIO()
    fastavro.schemaless_writer(buf, parsed_schema, VALID_USER_EVENT)
    expected_avro = buf.getvalue()
    assert msg.payload == expected_avro


@then(
    parsers.cfparse(
        'the SerializedMessage headers contain exactly the key "{header_name}"'
    )
)
def then_headers_contain_key(
    serialize_result: dict[str, Any], header_name: str
) -> None:
    msg: SerializedMessage = serialize_result["message"]
    assert header_name in msg.headers
    assert len(msg.headers) == 1


@then("an error is raised before any bytes are produced")
def then_error_raised(serialize_error_result: dict[str, Any]) -> None:
    assert serialize_error_result["error"] is not None


@then("no headers are set")
def then_no_headers(serialize_error_result: dict[str, Any]) -> None:
    """Verify no SerializedMessage was returned (error was raised)."""
    assert serialize_error_result["message"] is None


@then("the decoded record is identical to the original input data")
def then_decoded_equals_original(decoded_record: dict[str, Any]) -> None:
    assert decoded_record == VALID_USER_EVENT


@then("the SerializedMessage headers contain exactly one entry")
def then_headers_one_entry(serialize_result: dict[str, Any]) -> None:
    msg: SerializedMessage = serialize_result["message"]
    assert len(msg.headers) == 1


@then("the header value is exactly 8 bytes long")
def then_header_value_8_bytes(serialize_result: dict[str, Any]) -> None:
    msg: SerializedMessage = serialize_result["message"]
    values = list(msg.headers.values())
    assert len(values) == 1
    assert len(values[0]) == 8


@then('the header value bytes equal struct.pack(">q", schema_identifier)')
def then_header_value_matches_global_id(
    serialize_result: dict[str, Any],
) -> None:
    msg: SerializedMessage = serialize_result["message"]
    values = list(msg.headers.values())
    assert values[0] == struct.pack(">q", GLOBAL_ID)


@then('the SerializedMessage headers contain a key ending with ".contentId"')
def then_header_key_ends_with_content_id(
    serialize_result: dict[str, Any],
) -> None:
    msg: SerializedMessage = serialize_result["message"]
    keys = list(msg.headers.keys())
    assert len(keys) == 1
    assert keys[0].endswith(".contentId")


@then("the header value encodes the content identifier assigned by the registry")
def then_header_value_encodes_content_id(
    serialize_result: dict[str, Any],
) -> None:
    msg: SerializedMessage = serialize_result["message"]
    values = list(msg.headers.values())
    assert len(values) == 1
    decoded_id = struct.unpack(">q", values[0])[0]
    assert decoded_id == CONTENT_ID


@then("a SchemaNotFoundError is raised")
def then_schema_not_found_error(
    serialize_result: dict[str, Any],
) -> None:
    assert isinstance(serialize_result["error"], SchemaNotFoundError)


@then("no SerializedMessage is returned")
def then_no_serialized_message(serialize_result: dict[str, Any]) -> None:
    assert serialize_result["message"] is None


@then("exactly 1 HTTP call is made to the schema registry")
def then_one_http_call(mock_registry: respx.MockRouter) -> None:
    # The mock router tracks all calls. With caching, only 1 HTTP call should occur.
    assert mock_registry.calls.call_count == 1
