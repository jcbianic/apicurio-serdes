"""Step definitions for CONFLUENT_PAYLOAD compatibility scenarios [TS-010..TS-014].

RED phase: these tests import WireFormat and SerializedMessage which do not yet
exist in production code, and call serializer.serialize() which is not yet
implemented.  They are expected to fail with ImportError until the production
code is written.
"""

from __future__ import annotations

import dataclasses
import struct

import pytest
import respx
from pytest_bdd import given, scenario, then, when

from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroSerializer
from apicurio_serdes.serialization import MessageField, SerializationContext
from tests.conftest import (
    GLOBAL_ID,
    GROUP_ID,
    REGISTRY_URL,
    VALID_USER_EVENT,
    _schema_route,
)

# Imports that will fail until production code is written (RED phase).
# WireFormat and SerializedMessage do not yet exist in apicurio_serdes.serialization.
from apicurio_serdes.serialization import SerializedMessage, WireFormat

FEATURES_BASE = "../../specs/004-kafka-headers-wire-format/tests/features"
FEATURE = f"{FEATURES_BASE}/confluent_payload_compatibility.feature"


# ── Scenarios ──


@scenario(FEATURE, "Default serialization produces Confluent framing bytes")
def test_ts010_default_confluent_framing() -> None:
    """TS-010."""


@scenario(FEATURE, "Explicit CONFLUENT_PAYLOAD output is identical to default output")
def test_ts011_explicit_confluent_identical_to_default() -> None:
    """TS-011."""


@scenario(
    FEATURE,
    "serialize() returns SerializedMessage with empty headers for CONFLUENT_PAYLOAD",
)
def test_ts012_serialize_returns_serialized_message() -> None:
    """TS-012."""


@scenario(
    FEATURE,
    "__call__ return type is unchanged \u2014 returns bytes only",
)
def test_ts013_call_returns_bytes() -> None:
    """TS-013."""


@scenario(
    FEATURE,
    "SerializedMessage is immutable \u2014 mutation raises an error",
)
def test_ts014_serialized_message_immutable() -> None:
    """TS-014."""


# ── Given steps ──


@given(
    "an AvroSerializer configured without an explicit wire_format parameter",
    target_fixture="default_serializer",
)
def given_serializer_without_wire_format(
    mock_registry: respx.MockRouter,
) -> AvroSerializer:
    _schema_route(mock_registry, "UserEvent")
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    return AvroSerializer(registry_client=client, artifact_id="UserEvent")


@given(
    "an AvroSerializer configured with WireFormat.CONFLUENT_PAYLOAD",
    target_fixture="serializer",
)
def given_serializer_with_confluent_payload(
    mock_registry: respx.MockRouter,
) -> AvroSerializer:
    _schema_route(mock_registry, "UserEvent")
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    return AvroSerializer(
        registry_client=client,
        artifact_id="UserEvent",
        wire_format=WireFormat.CONFLUENT_PAYLOAD,
    )


@given("a schema artifact exists in the registry")
def given_schema_artifact_exists() -> None:
    """Schema route already registered in the serializer Given step."""


# ── When steps ──


@when(
    "the serializer is called with a valid dict and a SerializationContext",
    target_fixture="result_bytes",
)
def when_default_serializer_called(default_serializer: AvroSerializer) -> bytes:
    ctx = SerializationContext(topic="test-topic", field=MessageField.VALUE)
    return default_serializer(VALID_USER_EVENT, ctx)


@when(
    "the serializer is called with the same valid dict as the default serializer",
    target_fixture="explicit_result",
)
def when_explicit_serializer_called(
    serializer: AvroSerializer,
    mock_registry: respx.MockRouter,
) -> dict[str, bytes]:
    """Produce output from both an explicit CONFLUENT_PAYLOAD serializer and a
    default (no wire_format) serializer, so the Then step can compare them."""
    ctx = SerializationContext(topic="test-topic", field=MessageField.VALUE)
    explicit_bytes = serializer(VALID_USER_EVENT, ctx)

    # Create a second serializer with no wire_format for comparison.
    _schema_route(mock_registry, "UserEvent-default")
    default_client = ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)
    default_ser = AvroSerializer(
        registry_client=default_client, artifact_id="UserEvent-default"
    )
    default_bytes = default_ser(VALID_USER_EVENT, ctx)

    return {"explicit": explicit_bytes, "default": default_bytes}


@when(
    "the serialize() method is called with a valid dict and a SerializationContext",
    target_fixture="serialized_message",
)
def when_serialize_method_called(serializer: AvroSerializer) -> SerializedMessage:
    ctx = SerializationContext(topic="test-topic", field=MessageField.VALUE)
    return serializer.serialize(VALID_USER_EVENT, ctx)


@when(
    "__call__ is invoked with a valid dict and a SerializationContext",
    target_fixture="call_and_serialize",
)
def when_call_invoked(serializer: AvroSerializer) -> dict[str, object]:
    """Invoke both __call__ and serialize() to allow comparison in Then steps."""
    ctx = SerializationContext(topic="test-topic", field=MessageField.VALUE)
    call_result = serializer(VALID_USER_EVENT, ctx)
    serialize_result = serializer.serialize(VALID_USER_EVENT, ctx)
    return {"call_result": call_result, "serialize_result": serialize_result}


@when("an attempt is made to mutate the returned SerializedMessage.payload field")
def when_attempt_mutation(serialized_message: SerializedMessage) -> None:
    """Attempt to mutate the frozen dataclass — captured in Then step."""
    # The actual mutation attempt is checked in the Then step via pytest.raises.
    # We store the message for the Then step to act on.
    pass


# ── Then steps ──


@then("the returned bytes begin with magic byte 0x00")
def then_magic_byte(result_bytes: bytes) -> None:
    assert result_bytes[0:1] == b"\x00"


@then(
    "the returned bytes contain a 4-byte big-endian schema identifier at offset 1"
)
def then_4byte_be_schema_id(result_bytes: bytes) -> None:
    schema_id = struct.unpack(">I", result_bytes[1:5])[0]
    assert schema_id == GLOBAL_ID


@then(
    "the output bytes are identical to the output produced with no wire_format argument"
)
def then_explicit_equals_default(explicit_result: dict[str, bytes]) -> None:
    assert explicit_result["explicit"] == explicit_result["default"]


@then("the returned SerializedMessage.payload contains the Confluent-framed bytes")
def then_payload_confluent_framed(serialized_message: SerializedMessage) -> None:
    payload = serialized_message.payload
    assert payload[0:1] == b"\x00"
    schema_id = struct.unpack(">I", payload[1:5])[0]
    assert schema_id == GLOBAL_ID
    assert len(payload) > 5


@then("the returned SerializedMessage.headers is an empty dict")
def then_headers_empty(serialized_message: SerializedMessage) -> None:
    assert serialized_message.headers == {}


@then("the return value is of type bytes")
def then_call_returns_bytes(call_and_serialize: dict[str, object]) -> None:
    assert isinstance(call_and_serialize["call_result"], bytes)


@then("the return value is identical to SerializedMessage.payload from serialize()")
def then_call_equals_serialize_payload(
    call_and_serialize: dict[str, object],
) -> None:
    call_result = call_and_serialize["call_result"]
    serialize_result: SerializedMessage = call_and_serialize["serialize_result"]  # type: ignore[assignment]
    assert call_result == serialize_result.payload


@then("a FrozenInstanceError is raised")
def then_frozen_instance_error(serialized_message: SerializedMessage) -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        serialized_message.payload = b"changed"  # type: ignore[misc]
