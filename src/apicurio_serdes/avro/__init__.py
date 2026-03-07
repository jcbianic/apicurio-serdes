"""Avro serialization support for apicurio-serdes."""

from apicurio_serdes.avro._deserializer import AvroDeserializer
from apicurio_serdes.avro._serializer import AvroSerializer

__all__ = ["AvroDeserializer", "AvroSerializer"]
