"""Step definitions for TS-009: SerializationContext carries topic and field."""

from __future__ import annotations

from pytest_bdd import given, parsers, scenario, then

from apicurio_serdes.serialization import MessageField, SerializationContext


@scenario(
    "../../specs/001-avro-serializer/tests/features/avro_serialization.feature",
    "SerializationContext carries the Kafka topic name and field type",
)
def test_serialization_context_carries_topic_and_field() -> None:
    """TS-009."""


@given(
    parsers.cfparse('a SerializationContext constructed with topic "{topic}" and field {field}'),
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
