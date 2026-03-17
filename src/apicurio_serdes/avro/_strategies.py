"""Built-in artifact resolver strategies for AvroSerializer."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apicurio_serdes.serialization import SerializationContext

#: Type alias for an artifact resolver callable.
#: A resolver accepts a :class:`~apicurio_serdes.serialization.SerializationContext`
#: and returns the artifact ID string to look up in the registry.
ArtifactResolver = Callable[["SerializationContext"], str]


class TopicIdStrategy:
    """Derives the artifact ID from the topic name and message field.

    Returns ``"{topic}-{field}"`` (e.g. ``"orders-value"`` or
    ``"orders-key"``), matching the Apicurio Java reference implementation's
    ``TopicIdStrategy``.

    Example:
        ```python
        from apicurio_serdes.avro import TopicIdStrategy
        from apicurio_serdes.serialization import MessageField, SerializationContext

        strategy = TopicIdStrategy()
        ctx = SerializationContext(topic="orders", field=MessageField.VALUE)
        artifact_id = strategy(ctx)  # "orders-value"
        ```
    """

    def __call__(self, ctx: SerializationContext) -> str:
        """Return ``"{topic}-{field}"`` for the given context.

        Args:
            ctx: The serialization context containing the topic and field.

        Returns:
            Artifact ID string in the form ``"{topic}-{field}"``.
        """
        return f"{ctx.topic}-{ctx.field.value}"


class SimpleTopicIdStrategy:
    """Derives the artifact ID from the topic name only.

    Returns ``"{topic}"`` (e.g. ``"orders"``), matching the Apicurio Java
    reference implementation's ``SimpleTopicIdStrategy``.

    Example:
        ```python
        from apicurio_serdes.avro import SimpleTopicIdStrategy
        from apicurio_serdes.serialization import MessageField, SerializationContext

        strategy = SimpleTopicIdStrategy()
        ctx = SerializationContext(topic="orders", field=MessageField.VALUE)
        artifact_id = strategy(ctx)  # "orders"
        ```
    """

    def __call__(self, ctx: SerializationContext) -> str:
        """Return the topic name for the given context.

        Args:
            ctx: The serialization context containing the topic.

        Returns:
            The topic name as the artifact ID.
        """
        return ctx.topic


class QualifiedRecordIdStrategy:
    """Derives the artifact ID from the Avro schema's record name and namespace.

    Returns ``"{namespace}.{name}"`` when namespace is present, ``"{name}"``
    otherwise. Matches the Confluent ``RecordNameStrategy`` and Apicurio's
    qualified-record convention.

    The topic and message field are ignored — the artifact ID is fixed at
    construction time from the schema.

    Note:
        The Java ``RecordIdStrategy`` (groupId=namespace routing) is **not**
        implemented. Use the ``group_id`` parameter on the Apicurio client for
        that routing behaviour.

    Args:
        schema: Avro schema dict. Must contain a non-empty ``"name"`` key.

    Raises:
        ValueError: If ``schema`` has no ``"name"`` key or the name is empty.

    Example:
        ```python
        from apicurio_serdes.avro import QualifiedRecordIdStrategy

        schema = {"type": "record", "name": "Order", "namespace": "com.example", "fields": []}
        strategy = QualifiedRecordIdStrategy(schema)
        # strategy(ctx) == "com.example.Order"
        ```
    """

    def __init__(self, schema: dict[str, Any]) -> None:
        name = schema.get("name")
        if not name:
            raise ValueError("schema must have a non-empty 'name' field")
        namespace = schema.get("namespace")
        self._artifact_id = f"{namespace}.{name}" if namespace else name

    def __call__(self, ctx: SerializationContext) -> str:
        """Return the qualified record name, ignoring context.

        Args:
            ctx: The serialization context (unused).

        Returns:
            Artifact ID string in the form ``"{namespace}.{name}"`` or
            ``"{name}"``.
        """
        return self._artifact_id


class TopicRecordIdStrategy:
    """Derives the artifact ID from the topic and Avro schema's record name.

    Returns ``"{topic}-{namespace}.{name}"`` when namespace is present,
    ``"{topic}-{name}"`` otherwise. Matches the Confluent
    ``TopicRecordNameStrategy``.

    The artifact ID is partially fixed at construction time (record part) and
    partially resolved at call time (topic).

    Note:
        The Java ``RecordIdStrategy`` (groupId=namespace routing) is **not**
        implemented. Use the ``group_id`` parameter on the Apicurio client for
        that routing behaviour.

    Args:
        schema: Avro schema dict. Must contain a non-empty ``"name"`` key.

    Raises:
        ValueError: If ``schema`` has no ``"name"`` key or the name is empty.

    Example:
        ```python
        from apicurio_serdes.avro import TopicRecordIdStrategy
        from apicurio_serdes.serialization import MessageField, SerializationContext

        schema = {"type": "record", "name": "Order", "namespace": "com.example", "fields": []}
        strategy = TopicRecordIdStrategy(schema)
        ctx = SerializationContext(topic="orders", field=MessageField.VALUE)
        # strategy(ctx) == "orders-com.example.Order"
        ```
    """

    def __init__(self, schema: dict[str, Any]) -> None:
        name = schema.get("name")
        if not name:
            raise ValueError("schema must have a non-empty 'name' field")
        namespace = schema.get("namespace")
        self._record_part = f"{namespace}.{name}" if namespace else name

    def __call__(self, ctx: SerializationContext) -> str:
        """Return ``"{topic}-{record}"`` for the given context.

        Args:
            ctx: The serialization context containing the topic.

        Returns:
            Artifact ID string in the form ``"{topic}-{namespace}.{name}"``
            or ``"{topic}-{name}"``.
        """
        return f"{ctx.topic}-{self._record_part}"
