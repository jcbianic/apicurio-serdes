"""Avro serializer with Confluent wire format framing."""

from __future__ import annotations

import io
import struct
from typing import TYPE_CHECKING, Any

import fastavro

from apicurio_serdes._errors import SerializationError

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Literal

    from apicurio_serdes._client import ApicurioRegistryClient, CachedSchema
    from apicurio_serdes.serialization import SerializationContext


class AvroSerializer:
    """Serializes Python data to Confluent-framed Avro bytes.

    Fetches the Avro schema from the registry on first call and
    caches it via the underlying ApicurioRegistryClient.

    Args:
        registry_client: An ApicurioRegistryClient instance.
        artifact_id: The artifact identifier for the target schema.
        to_dict: Optional callable that converts input data to a dict
                 before Avro encoding. Signature: (data, ctx) -> dict.
                 When None, input is passed directly to the encoder (FR-007).
        use_id: Which registry ID to embed in the wire format header.
        strict: When True, reject extra fields not in the schema.
    """

    def __init__(
        self,
        registry_client: ApicurioRegistryClient,
        artifact_id: str,
        to_dict: Callable[[Any, SerializationContext], dict[str, Any]] | None = None,
        use_id: Literal["globalId", "contentId"] = "globalId",
        strict: bool = False,
    ) -> None:
        self.registry_client = registry_client
        self.artifact_id = artifact_id
        self.to_dict = to_dict
        self.use_id = use_id
        self.strict = strict
        self._schema: CachedSchema | None = None
        self._parsed_schema: dict[str, Any] | None = None

    def __call__(self, data: Any, ctx: SerializationContext) -> bytes:
        """Serialize data to Confluent-framed Avro bytes.

        Output format (FR-003):
          Byte 0:    Magic byte 0x00
          Bytes 1-4: schema identifier as 4-byte big-endian unsigned int
          Bytes 5+:  Avro binary payload (schemaless encoding)

        Args:
            data: The data to serialize. Must be a dict (or convertible
                  via to_dict) conforming to the Avro schema.
            ctx: Serialization context with topic and field metadata.

        Returns:
            Confluent wire format bytes.

        Raises:
            SchemaNotFoundError: If the artifact_id does not exist.
            RegistryConnectionError: If the registry is unreachable.
            SerializationError: If the to_dict callable raises an exception.
            ValueError: If data does not conform to the Avro schema.
        """
        # Lazy schema fetch (cached by client)
        if self._schema is None:
            cached = self.registry_client.get_schema(self.artifact_id)
            self._schema = cached
            self._parsed_schema = fastavro.parse_schema(cached.schema)

        # Apply to_dict hook if provided (FR-007, FR-013)
        if self.to_dict is not None:
            try:
                data = self.to_dict(data, ctx)
            except Exception as exc:
                raise SerializationError(exc) from exc

        # Strict mode validation (FR-012)
        if self.strict:
            schema_fields = {f["name"] for f in self._schema.schema["fields"]}
            extra = set(data.keys()) - schema_fields
            if extra:
                raise ValueError(
                    f"Extra fields not in schema: {', '.join(sorted(extra))}"
                )

        # Select wire format ID (FR-010)
        if self.use_id == "contentId":
            schema_id = self._schema.content_id
        else:
            schema_id = self._schema.global_id

        # Encode to Avro binary
        buffer = io.BytesIO()
        fastavro.schemaless_writer(buffer, self._parsed_schema, data)

        # Confluent wire format: 0x00 + 4-byte ID + Avro payload
        header = b"\x00" + struct.pack(">I", schema_id)
        return header + buffer.getvalue()
