"""Kafka serialization context and message field types."""

from __future__ import annotations

import enum
from dataclasses import dataclass


class MessageField(enum.Enum):
    """Identifies whether serialized data is a Kafka key or value.

    Mirrors confluent-kafka's MessageField enum (SC-004).
    """

    KEY = "key"
    VALUE = "value"


@dataclass(frozen=True)
class SerializationContext:
    """Carries Kafka metadata at serialization time.

    Mirrors confluent-kafka's SerializationContext interface (SC-004).

    Args:
        topic: The target Kafka topic name.
        field: Whether this datum is a message key or value.
    """

    topic: str
    field: MessageField
