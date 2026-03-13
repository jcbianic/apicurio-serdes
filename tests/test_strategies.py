"""Unit tests for artifact resolver strategies."""

from __future__ import annotations

from apicurio_serdes.avro import ArtifactResolver, SimpleTopicIdStrategy, TopicIdStrategy
from apicurio_serdes.serialization import MessageField, SerializationContext


def _ctx(topic: str, field: MessageField) -> SerializationContext:
    return SerializationContext(topic=topic, field=field)


class TestTopicIdStrategy:
    def test_value_field(self) -> None:
        strategy = TopicIdStrategy()
        assert strategy(_ctx("orders", MessageField.VALUE)) == "orders-value"

    def test_key_field(self) -> None:
        strategy = TopicIdStrategy()
        assert strategy(_ctx("orders", MessageField.KEY)) == "orders-key"

    def test_hyphenated_topic(self) -> None:
        strategy = TopicIdStrategy()
        assert strategy(_ctx("my-topic", MessageField.VALUE)) == "my-topic-value"


class TestSimpleTopicIdStrategy:
    def test_value_field(self) -> None:
        strategy = SimpleTopicIdStrategy()
        assert strategy(_ctx("orders", MessageField.VALUE)) == "orders"

    def test_key_field(self) -> None:
        strategy = SimpleTopicIdStrategy()
        assert strategy(_ctx("orders", MessageField.KEY)) == "orders"


def test_lambda_satisfies_artifact_resolver_protocol() -> None:
    """A plain lambda satisfies the ArtifactResolver type alias."""
    resolver: ArtifactResolver = lambda ctx: "static"  # noqa: E731
    ctx = _ctx("any-topic", MessageField.VALUE)
    assert resolver(ctx) == "static"
