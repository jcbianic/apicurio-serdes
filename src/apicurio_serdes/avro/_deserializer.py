"""Avro deserializer with Confluent wire format parsing."""

from __future__ import annotations

import io
import struct
from typing import TYPE_CHECKING, Any

import fastavro

from apicurio_serdes._errors import DeserializationError

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Literal

    from apicurio_serdes._client import ApicurioRegistryClient
    from apicurio_serdes.serialization import SerializationContext


class AvroDeserializer:
    """Deserializes Confluent-framed Avro bytes to Python dicts.

    Reads the wire format header to extract the schema identifier,
    resolves the schema from the registry, and decodes the Avro
    payload. Optionally applies a from_dict transformation hook.

    Args:
        registry_client: An ApicurioRegistryClient instance.
        from_dict: Optional callable that converts the decoded dict
                   to a domain object. Signature: (data, ctx) -> Any.
                   When None, the decoded dict is returned directly (FR-008).
        use_id: Which registry identifier type the 4-byte wire format
                field represents. Must match the serializer's use_id
                setting. Defaults to "globalId".
        reader_schema: Optional Avro schema dict used as the reader schema
                       during deserialization. When provided, fastavro
                       performs schema resolution between the writer schema
                       (embedded in the message) and this reader schema,
                       enabling field defaults to fill gaps for added fields,
                       type promotions, and other Avro evolution rules. When
                       None (default), the writer schema is used for both
                       roles (no evolution). Parsed once at construction time.
    """

    def __init__(
        self,
        registry_client: ApicurioRegistryClient,
        from_dict: Callable[[dict[str, Any], SerializationContext], Any] | None = None,
        use_id: Literal["globalId", "contentId"] = "globalId",
        *,
        reader_schema: dict[str, Any] | None = None,
    ) -> None:
        self.registry_client = registry_client
        self.from_dict = from_dict
        self.use_id = use_id
        self._parsed_cache: dict[int, Any] = {}
        self._parsed_reader_schema = (
            fastavro.parse_schema(reader_schema) if reader_schema is not None else None
        )

    def __call__(self, data: bytes, ctx: SerializationContext) -> Any:
        """Deserialize Confluent-framed Avro bytes.

        Input format (FR-003):
          Byte 0:    Magic byte 0x00
          Bytes 1-4: Schema identifier as 4-byte big-endian unsigned int
          Bytes 5+:  Avro binary payload (schemaless encoding)

        Args:
            data: Confluent wire format bytes to deserialize.
            ctx: Serialization context with topic and field metadata.

        Returns:
            A Python dict (or the result of from_dict if configured).

        Raises:
            DeserializationError: If the input is fewer than 5 bytes (FR-004),
                the magic byte is not 0x00 (FR-003), the Avro payload cannot
                be decoded (FR-011), or the from_dict callable raises an
                exception (FR-009).
            SchemaNotFoundError: If the schema identifier does not correspond
                to any schema in the registry (FR-010).
            RegistryConnectionError: If the registry is unreachable during
                schema resolution (FR-012).
        """
        # FR-004: validate minimum length
        if len(data) < 5:
            raise DeserializationError(
                f"Input too short: expected at least 5 bytes, got {len(data)}"
            )

        # FR-003: validate magic byte
        if data[0] != 0x00:
            raise DeserializationError(
                f"Invalid magic byte: expected 0x00, got {data[0]:#04x}"
            )

        # Extract schema identifier from bytes 1-4
        schema_id: int = struct.unpack(">I", data[1:5])[0]

        # FR-005, FR-006: resolve schema by ID type
        if self.use_id == "globalId":
            schema_dict = self.registry_client.get_schema_by_global_id(schema_id)
        else:
            schema_dict = self.registry_client.get_schema_by_content_id(schema_id)

        # Cache parsed schema to avoid repeated parse_schema calls (FR-007)
        if schema_id not in self._parsed_cache:
            self._parsed_cache[schema_id] = fastavro.parse_schema(schema_dict)
        parsed_schema = self._parsed_cache[schema_id]

        # FR-011: decode Avro payload
        try:
            result: Any = fastavro.schemaless_reader(
                io.BytesIO(data[5:]), parsed_schema, self._parsed_reader_schema
            )
        except Exception as exc:
            raise DeserializationError(
                f"Avro decode failure: {exc}", cause=exc
            ) from exc

        # FR-008, FR-009: apply from_dict hook if configured
        if self.from_dict is not None:
            try:
                return self.from_dict(result, ctx)
            except Exception as exc:
                raise DeserializationError(
                    f"from_dict conversion failed: {exc}", cause=exc
                ) from exc

        return result
