"""Async Avro deserializer with Confluent wire format parsing."""

from __future__ import annotations

import io
import struct
from typing import TYPE_CHECKING, Any

import fastavro

from apicurio_serdes._errors import DeserializationError

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Literal

    from apicurio_serdes._async_client import AsyncApicurioRegistryClient
    from apicurio_serdes.serialization import SerializationContext


class AsyncAvroDeserializer:
    """Deserializes Confluent-framed Avro bytes to Python dicts (async).

    Non-blocking counterpart to AvroDeserializer. Uses
    AsyncApicurioRegistryClient for schema resolution, making it
    suitable for use in fully async services without blocking the
    event loop.

    Args:
        registry_client: An AsyncApicurioRegistryClient instance.
        from_dict: Optional callable that converts the decoded dict
                   to a domain object. Signature: (data, ctx) -> Any.
                   When None, the decoded dict is returned directly.
        use_id: Which registry identifier type the 4-byte wire format
                field represents. Must match the serializer's use_id
                setting. Defaults to "contentId".

    Example:
        ```python
        from apicurio_serdes import AsyncApicurioRegistryClient
        from apicurio_serdes.avro import AsyncAvroDeserializer
        from apicurio_serdes.serialization import SerializationContext, MessageField

        client = AsyncApicurioRegistryClient(
            url="http://localhost:8080/apis/registry/v3",
            group_id="com.example.schemas",
        )
        deserializer = AsyncAvroDeserializer(registry_client=client)
        ctx = SerializationContext(topic="user-events", field=MessageField.VALUE)

        async with client:
            result = await deserializer(raw_bytes, ctx)
        ```
    """

    def __init__(
        self,
        registry_client: AsyncApicurioRegistryClient,
        from_dict: Callable[[dict[str, Any], SerializationContext], Any] | None = None,
        use_id: Literal["globalId", "contentId"] = "contentId",
    ) -> None:
        self.registry_client = registry_client
        self.from_dict = from_dict
        self.use_id = use_id
        self._parsed_cache: dict[int, Any] = {}

    async def __call__(self, data: bytes, ctx: SerializationContext) -> Any:
        """Deserialize Confluent-framed Avro bytes (async).

        Input format:
          Byte 0:    Magic byte 0x00
          Bytes 1-4: Schema identifier as 4-byte big-endian unsigned int
          Bytes 5+:  Avro binary payload (schemaless encoding)

        Args:
            data: Confluent wire format bytes to deserialize.
            ctx: Serialization context with topic and field metadata.

        Returns:
            A Python dict (or the result of from_dict if configured).

        Raises:
            DeserializationError: If the input is fewer than 5 bytes,
                the magic byte is not 0x00, the Avro payload cannot be
                decoded, or the from_dict callable raises an exception.
            SchemaNotFoundError: If the schema identifier does not
                correspond to any schema in the registry.
            RegistryConnectionError: If the registry is unreachable
                during schema resolution.
        """
        if len(data) < 5:
            raise DeserializationError(
                f"Input too short: expected at least 5 bytes, got {len(data)}"
            )

        if data[0] != 0x00:
            raise DeserializationError(
                f"Invalid magic byte: expected 0x00, got {data[0]:#04x}"
            )

        schema_id: int = struct.unpack(">I", data[1:5])[0]

        if self.use_id == "globalId":
            schema_dict = await self.registry_client.get_schema_by_global_id(schema_id)
        else:
            schema_dict = await self.registry_client.get_schema_by_content_id(schema_id)

        if schema_id not in self._parsed_cache:
            self._parsed_cache[schema_id] = fastavro.parse_schema(schema_dict)
        parsed_schema = self._parsed_cache[schema_id]

        try:
            result: Any = fastavro.schemaless_reader(
                io.BytesIO(data[5:]), parsed_schema, parsed_schema
            )
        except Exception as exc:
            raise DeserializationError(
                f"Avro decode failure: {exc}", cause=exc
            ) from exc

        if self.from_dict is not None:
            try:
                return self.from_dict(result, ctx)
            except Exception as exc:
                raise DeserializationError(
                    f"from_dict conversion failed: {exc}", cause=exc
                ) from exc

        return result
