"""Avro serialization support for apicurio-serdes."""

from apicurio_serdes.avro._async_deserializer import AsyncAvroDeserializer
from apicurio_serdes.avro._deserializer import AvroDeserializer
from apicurio_serdes.avro._serializer import AvroSerializer
from apicurio_serdes.avro._strategies import (
    ArtifactResolver,
    SimpleTopicIdStrategy,
    TopicIdStrategy,
)

__all__ = [
    "ArtifactResolver",
    "AsyncAvroDeserializer",
    "AvroDeserializer",
    "AvroSerializer",
    "SimpleTopicIdStrategy",
    "TopicIdStrategy",
]
