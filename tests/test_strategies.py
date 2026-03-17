"""Unit tests for artifact resolver strategies."""

from __future__ import annotations

import pytest

from apicurio_serdes.avro import (
    ArtifactResolver,
    QualifiedRecordIdStrategy,
    SimpleTopicIdStrategy,
    TopicIdStrategy,
    TopicRecordIdStrategy,
)
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


class TestQualifiedRecordIdStrategy:
    def test_with_namespace(self) -> None:
        strategy = QualifiedRecordIdStrategy({"name": "Order", "namespace": "com.example"})
        assert strategy(_ctx("orders", MessageField.VALUE)) == "com.example.Order"

    def test_without_namespace(self) -> None:
        strategy = QualifiedRecordIdStrategy({"name": "Order"})
        assert strategy(_ctx("orders", MessageField.VALUE)) == "Order"

    def test_field_ignored(self) -> None:
        strategy = QualifiedRecordIdStrategy({"name": "Order", "namespace": "com.example"})
        assert strategy(_ctx("orders", MessageField.KEY)) == "com.example.Order"

    def test_no_name_raises(self) -> None:
        with pytest.raises(ValueError):
            QualifiedRecordIdStrategy({})

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError):
            QualifiedRecordIdStrategy({"name": ""})

    def test_callable(self) -> None:
        strategy = QualifiedRecordIdStrategy({"name": "Order"})
        assert callable(strategy)

    def test_returns_str(self) -> None:
        strategy = QualifiedRecordIdStrategy({"name": "Order"})
        result = strategy(_ctx("orders", MessageField.VALUE))
        assert isinstance(result, str)


class TestTopicRecordIdStrategy:
    def test_with_namespace_value(self) -> None:
        strategy = TopicRecordIdStrategy({"name": "Order", "namespace": "com.example"})
        assert strategy(_ctx("orders", MessageField.VALUE)) == "orders-com.example.Order"

    def test_with_namespace_key(self) -> None:
        strategy = TopicRecordIdStrategy({"name": "Order", "namespace": "com.example"})
        assert strategy(_ctx("orders", MessageField.KEY)) == "orders-com.example.Order"

    def test_without_namespace(self) -> None:
        strategy = TopicRecordIdStrategy({"name": "Order"})
        assert strategy(_ctx("orders", MessageField.VALUE)) == "orders-Order"

    def test_no_name_raises(self) -> None:
        with pytest.raises(ValueError):
            TopicRecordIdStrategy({})

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError):
            TopicRecordIdStrategy({"name": ""})

    def test_callable(self) -> None:
        strategy = TopicRecordIdStrategy({"name": "Order"})
        assert callable(strategy)

    def test_returns_str(self) -> None:
        strategy = TopicRecordIdStrategy({"name": "Order"})
        result = strategy(_ctx("orders", MessageField.VALUE))
        assert isinstance(result, str)


def test_lambda_satisfies_artifact_resolver_protocol() -> None:
    """A plain lambda satisfies the ArtifactResolver type alias."""
    resolver: ArtifactResolver = lambda ctx: "static"  # noqa: E731
    ctx = _ctx("any-topic", MessageField.VALUE)
    assert resolver(ctx) == "static"
