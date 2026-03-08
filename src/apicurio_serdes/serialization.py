"""Kafka serialization context, message field types, and wire format configuration."""

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


class WireFormat(enum.Enum):
    """Selects the wire format framing for an AvroSerializer.

    Members:
        CONFLUENT_PAYLOAD: Default. Schema identifier embedded in message bytes
            as a magic byte (0x00) + 4-byte big-endian uint32 prefix.
        KAFKA_HEADERS: Schema identifier communicated as a Kafka message header.
            Message bytes contain only the raw Avro binary payload.
    """

    CONFLUENT_PAYLOAD = "CONFLUENT_PAYLOAD"
    KAFKA_HEADERS = "KAFKA_HEADERS"


@dataclass(frozen=True)
class SerializedMessage:
    """Result of AvroSerializer.serialize().

    Carries the serialized payload bytes and any Kafka message headers
    produced by the chosen wire format mode.

    Attributes:
        payload: The serialized message body.
            For CONFLUENT_PAYLOAD: framed bytes (magic byte + 4-byte ID + Avro).
            For KAFKA_HEADERS: raw Avro binary only (no prefix).
        headers: Kafka message headers to attach to the produced record.
            For CONFLUENT_PAYLOAD: always empty dict {}.
            For KAFKA_HEADERS: one entry {header_name: header_value} where
            header_name follows Apicurio's native naming convention and
            header_value is the schema ID encoded as 8-byte big-endian signed long.
    """

    payload: bytes
    headers: dict[str, bytes]
