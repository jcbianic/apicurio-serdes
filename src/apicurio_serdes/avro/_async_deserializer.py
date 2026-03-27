"""Async Avro deserializer with Confluent wire format parsing."""

from __future__ import annotations

import struct
from typing import TYPE_CHECKING, Any

import fastavro

from apicurio_serdes._errors import DeserializationError
from apicurio_serdes.avro._deserializer import _BaseAvroDeserializer

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Literal

    from apicurio_serdes._async_client import AsyncApicurioRegistryClient
    from apicurio_serdes.avro._strategies import ArtifactResolver
    from apicurio_serdes.serialization import SerializationContext


class AsyncAvroDeserializer(_BaseAvroDeserializer):
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
                setting. Defaults to "globalId".
        artifact_id: Artifact identifier used to fetch the latest registry
                     schema as the reader schema. Requires
                     ``use_latest_version=True``. Mutually exclusive with
                     ``artifact_resolver``.
        artifact_resolver: Callable ``(ctx) -> str`` that returns the
                           artifact identifier at call time. Requires
                           ``use_latest_version=True``. Mutually exclusive
                           with ``artifact_id``. The resolved value is cached
                           after the first successful call.
        use_latest_version: When ``True``, fetches the latest registry schema
                            for the resolved artifact on the first call and
                            uses it as the reader schema (cached per instance).
                            Requires ``artifact_id`` or ``artifact_resolver``.
                            Mutually exclusive with ``reader_schema``.
        reader_schema: Optional Avro schema dict used as the reader schema
                       during deserialization. When provided, fastavro
                       performs schema resolution between the writer schema
                       (embedded in the message) and this reader schema,
                       enabling field defaults to fill gaps for added fields,
                       type promotions, and other Avro evolution rules. When
                       None (default), the writer schema is used for both
                       roles (no evolution). Parsed once at construction time.
                       Mutually exclusive with ``use_latest_version``.

    Raises:
        ValueError: If ``artifact_id`` and ``artifact_resolver`` are both
                    provided, if ``use_latest_version=True`` is used without
                    ``artifact_id`` or ``artifact_resolver``, if
                    ``use_latest_version=True`` is combined with
                    ``reader_schema``, or if ``artifact_id`` /
                    ``artifact_resolver`` is provided without
                    ``use_latest_version=True``.

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
        use_id: Literal["globalId", "contentId"] = "globalId",
        *,
        artifact_id: str | None = None,
        artifact_resolver: ArtifactResolver | None = None,
        use_latest_version: bool = False,
        reader_schema: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            from_dict=from_dict,
            use_id=use_id,
            reader_schema=reader_schema,
            artifact_id=artifact_id,
            artifact_resolver=artifact_resolver,
            use_latest_version=use_latest_version,
        )
        self.registry_client = registry_client

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

        if self._use_latest_version and self._parsed_reader_schema is None:
            effective_id = self._resolve_artifact_id(ctx)
            cached = await self.registry_client.get_schema(effective_id)
            self._parsed_reader_schema = fastavro.parse_schema(cached.schema)

        return self._decode(schema_id, schema_dict, data[5:], ctx)
