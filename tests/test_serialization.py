"""Step definitions for TS-009: SerializationContext carries topic and field."""

from __future__ import annotations

from pytest_bdd import given, parsers, scenario, then

from apicurio_serdes.serialization import MessageField, SerializationContext


@scenario(
    "../specs/001-avro-serializer/tests/features/avro_serialization.feature",
    "SerializationContext carries the Kafka topic name and field type",
)
def test_serialization_context_carries_topic_and_field() -> None:
    """TS-009."""


@given(
    parsers.cfparse(
        'a SerializationContext constructed with topic "{topic}" and field {field}'
    ),
    target_fixture="ctx",
)
def given_serialization_context(topic: str, field: str) -> SerializationContext:
    return SerializationContext(topic=topic, field=MessageField[field])


@then(parsers.cfparse('the context exposes topic "{topic}"'))
def then_context_exposes_topic(ctx: SerializationContext, topic: str) -> None:
    assert ctx.topic == topic


@then(parsers.cfparse("the context exposes field {field}"))
def then_context_exposes_field(ctx: SerializationContext, field: str) -> None:
    assert ctx.field == MessageField[field]


# ---------------------------------------------------------------------------
# T003 — Failing unit tests for WireFormat enum and SerializedMessage dataclass
# ---------------------------------------------------------------------------

import enum

import pytest

from apicurio_serdes.serialization import SerializedMessage, WireFormat  # noqa: E402


# ---- WireFormat enum tests ------------------------------------------------


class TestWireFormatEnum:
    """Unit tests for the WireFormat enum (T003)."""

    def test_confluent_payload_member_exists(self) -> None:
        """WireFormat.CONFLUENT_PAYLOAD exists and has the expected value."""
        assert WireFormat.CONFLUENT_PAYLOAD.value == "CONFLUENT_PAYLOAD"

    def test_kafka_headers_member_exists(self) -> None:
        """WireFormat.KAFKA_HEADERS exists and has the expected value."""
        assert WireFormat.KAFKA_HEADERS.value == "KAFKA_HEADERS"

    def test_is_enum_subclass(self) -> None:
        """WireFormat is a subclass of enum.Enum."""
        assert issubclass(WireFormat, enum.Enum)

    def test_exactly_two_members(self) -> None:
        """Iterating over WireFormat yields exactly 2 members."""
        assert len(list(WireFormat)) == 2


# ---- SerializedMessage dataclass tests ------------------------------------


class TestSerializedMessage:
    """Unit tests for the SerializedMessage frozen dataclass (T003)."""

    def test_construction_with_payload_and_headers(self) -> None:
        """SerializedMessage can be constructed with payload and headers."""
        msg = SerializedMessage(payload=b"data", headers={})
        assert msg.payload == b"data"
        assert msg.headers == {}

    def test_frozen_cannot_set_payload(self) -> None:
        """SerializedMessage is frozen — setting .payload raises an error."""
        msg = SerializedMessage(payload=b"data", headers={})
        with pytest.raises(AttributeError):
            msg.payload = b"other"  # type: ignore[misc]

    def test_payload_is_bytes(self) -> None:
        """The payload field holds bytes."""
        msg = SerializedMessage(payload=b"\x00\x01", headers={})
        assert isinstance(msg.payload, bytes)

    def test_headers_is_dict(self) -> None:
        """The headers field holds a dict."""
        msg = SerializedMessage(payload=b"data", headers={})
        assert isinstance(msg.headers, dict)

    def test_kafka_headers_style_construction(self) -> None:
        """SerializedMessage accepts KAFKA_HEADERS-style headers."""
        headers = {"apicurio.value.globalId": b"\x00" * 8}
        msg = SerializedMessage(payload=b"avro-bytes", headers=headers)
        assert msg.headers == {"apicurio.value.globalId": b"\x00" * 8}
        assert len(msg.headers["apicurio.value.globalId"]) == 8
