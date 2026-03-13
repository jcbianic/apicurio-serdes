"""Built-in artifact resolver strategies for AvroSerializer."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

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
