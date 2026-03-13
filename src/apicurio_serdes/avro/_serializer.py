"""Avro serializer with configurable wire format framing."""

from __future__ import annotations

import io
import struct
from typing import TYPE_CHECKING, Any

import fastavro

from apicurio_serdes._errors import ResolverError, SerializationError
from apicurio_serdes.serialization import SerializedMessage, WireFormat

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Literal

    from apicurio_serdes._client import ApicurioRegistryClient, CachedSchema
    from apicurio_serdes.avro._strategies import ArtifactResolver
    from apicurio_serdes.serialization import SerializationContext


class AvroSerializer:
    """Serializes Python data to Avro bytes with configurable wire format framing.

    Fetches the Avro schema from the registry on first call and
    caches it via the underlying
    [ApicurioRegistryClient][apicurio_serdes._client.ApicurioRegistryClient].

    Args:
        registry_client: An
            [ApicurioRegistryClient][apicurio_serdes._client.ApicurioRegistryClient]
            instance.
        artifact_id: The static artifact identifier for the target schema.
            Mutually exclusive with ``artifact_resolver``.
        artifact_resolver: A callable ``(ctx) -> str`` that derives the
            artifact ID from the serialization context at first serialize.
            Mutually exclusive with ``artifact_id``. Built-in strategies:
            :class:`~apicurio_serdes.avro.TopicIdStrategy` and
            :class:`~apicurio_serdes.avro.SimpleTopicIdStrategy`.
        to_dict: Optional callable that converts input data to a dict
                 before Avro encoding. Signature: ``(data, ctx) -> dict``.
                 When ``None``, input is passed directly to the encoder.
        use_id: Which registry-assigned identifier to use as the schema ID.
                ``"globalId"`` (default) or ``"contentId"``. Applies to both wire
                format modes.
        strict: When ``True``, reject extra fields not in the schema.
        wire_format: The wire format framing mode. Defaults to
                     WireFormat.CONFLUENT_PAYLOAD (FR-003).

    Raises:
        ValueError: If both or neither of ``artifact_id`` / ``artifact_resolver``
            are provided, if ``wire_format`` is not a WireFormat enum member, or
            if ``use_id`` is not ``"globalId"`` or ``"contentId"``.

    Example:
        ```python
        from apicurio_serdes import ApicurioRegistryClient
        from apicurio_serdes.avro import AvroSerializer, TopicIdStrategy
        from apicurio_serdes.serialization import (
            SerializationContext,
            MessageField,
        )

        client = ApicurioRegistryClient(
            url="http://localhost:8080/apis/registry/v3",
            group_id="com.example.schemas",
        )
        serializer = AvroSerializer(
            registry_client=client,
            artifact_resolver=TopicIdStrategy(),
        )
        ctx = SerializationContext(
            topic="user-events", field=MessageField.VALUE,
        )
        payload: bytes = serializer(
            {"userId": "abc-123", "country": "FR"}, ctx,
        )
        ```
    """

    _VALID_USE_ID = frozenset({"globalId", "contentId"})

    def __init__(
        self,
        registry_client: ApicurioRegistryClient,
        artifact_id: str | None = None,
        artifact_resolver: ArtifactResolver | None = None,
        to_dict: Callable[[Any, SerializationContext], dict[str, Any]] | None = None,
        use_id: Literal["globalId", "contentId"] = "globalId",
        strict: bool = False,
        wire_format: WireFormat = WireFormat.CONFLUENT_PAYLOAD,
    ) -> None:
        if artifact_id is not None and artifact_resolver is not None:
            raise ValueError(
                "artifact_id and artifact_resolver are mutually exclusive; "
                "provide exactly one."
            )
        if artifact_id is None and artifact_resolver is None:
            raise ValueError("One of artifact_id or artifact_resolver is required.")
        if not isinstance(wire_format, WireFormat):
            raise ValueError(
                f"wire_format must be a WireFormat enum member, got {wire_format!r}"
            )
        if use_id not in self._VALID_USE_ID:
            raise ValueError(
                f"use_id must be 'globalId' or 'contentId', got {use_id!r}"
            )
        self.registry_client = registry_client
        self.artifact_id: str | None = artifact_id
        self._artifact_resolver: ArtifactResolver | None = artifact_resolver
        self._resolved_artifact_id: str | None = None
        self.to_dict = to_dict
        self.use_id = use_id
        self.strict = strict
        self.wire_format = wire_format
        self._schema: CachedSchema | None = None
        self._parsed_schema: str | list[Any] | dict[Any, Any] | None = None

    def serialize(self, data: Any, ctx: SerializationContext) -> SerializedMessage:
        """Serialize data and return payload bytes plus any Kafka headers.

        For CONFLUENT_PAYLOAD: returns framed bytes (unchanged from __call__)
        with an empty headers dict.
        For KAFKA_HEADERS: returns raw Avro binary as payload and a one-entry
        headers dict with the schema ID encoded per Apicurio's native convention.

        Args:
            data: The data to serialize. Must be a dict (or convertible
                  via to_dict) conforming to the Avro schema.
            ctx: Serialization context with topic and field metadata.

        Returns:
            SerializedMessage with payload bytes and headers dict.

        Raises:
            ResolverError: If the artifact_resolver raises or returns something other
                than a non-empty str.
            SchemaNotFoundError: If the resolved artifact does not exist in the registry.
            RegistryConnectionError: If the registry is unreachable.
            SerializationError: If the to_dict callable raises an exception.
            ValueError: If data does not conform to the Avro schema.
        """
        # Lazy schema fetch (cached by client)
        if self._schema is None:
            if (
                self._artifact_resolver is not None
                and self._resolved_artifact_id is None
            ):
                try:
                    resolved = self._artifact_resolver(ctx)
                except Exception as exc:
                    raise ResolverError(
                        f"artifact_resolver raised: {exc}", cause=exc
                    ) from exc
                if not isinstance(resolved, str) or not resolved:
                    raise ResolverError(
                        f"artifact_resolver must return a non-empty str, got {resolved!r}"
                    )
                self._resolved_artifact_id = resolved
            effective_id = (
                self.artifact_id
                if self.artifact_id is not None
                else self._resolved_artifact_id
            )
            if effective_id is None:  # pragma: no cover
                raise RuntimeError(
                    "artifact_id is None and no resolver has produced an ID yet; "
                    "this is an internal invariant violation."
                )
            cached = self.registry_client.get_schema(effective_id)
            self._schema = cached
            self._parsed_schema = fastavro.parse_schema(cached.schema)

        # Apply to_dict hook if provided
        if self.to_dict is not None:
            try:
                data = self.to_dict(data, ctx)
            except Exception as exc:
                raise SerializationError(exc) from exc

        # Strict mode validation
        if self.strict:
            fields = self._schema.schema.get("fields")
            if fields is None:
                raise ValueError("strict mode requires a record schema with 'fields'")
            schema_fields = {f["name"] for f in fields}
            extra = set(data.keys()) - schema_fields
            if extra:
                raise ValueError(
                    f"Extra fields not in schema: {', '.join(sorted(extra))}"
                )

        # Select schema ID based on use_id
        if self.use_id == "contentId":
            schema_id = self._schema.content_id
        else:
            schema_id = self._schema.global_id

        # Encode to Avro binary
        buffer = io.BytesIO()
        if self._parsed_schema is None:  # pragma: no cover
            raise RuntimeError(
                "_parsed_schema unexpectedly None after lazy schema fetch"
            )
        fastavro.schemaless_writer(buffer, self._parsed_schema, data)
        avro_bytes = buffer.getvalue()

        if self.wire_format == WireFormat.KAFKA_HEADERS:
            # KAFKA_HEADERS: raw Avro payload, schema ID in headers
            header_name = f"apicurio.{ctx.field.value}.{self.use_id}"
            header_value = struct.pack(">q", schema_id)
            return SerializedMessage(
                payload=avro_bytes,
                headers={header_name: header_value},
            )

        # CONFLUENT_PAYLOAD: 0x00 + 4-byte ID + Avro payload
        uint32_max = 2**32 - 1
        if not (0 <= schema_id <= uint32_max):
            raise ValueError(
                f"Schema ID {schema_id} exceeds the unsigned 32-bit limit "
                f"({uint32_max}) required by CONFLUENT_PAYLOAD wire format. "
                f"Use WireFormat.KAFKA_HEADERS for 64-bit ID support."
            )
        framed = b"\x00" + struct.pack(">I", schema_id) + avro_bytes
        return SerializedMessage(payload=framed, headers={})

    def __call__(self, data: Any, ctx: SerializationContext) -> bytes:
        """Serialize data to bytes. Delegates to serialize() and returns payload.

        Only supported for CONFLUENT_PAYLOAD wire format. For KAFKA_HEADERS,
        use serialize() which returns a SerializedMessage with both payload
        and headers.

        Args:
            data: The data to serialize. Must be a dict (or convertible
                  via to_dict) conforming to the Avro schema.
            ctx: Serialization context with topic and field metadata.

        Returns:
            Serialized bytes (CONFLUENT_PAYLOAD framed).

        Raises:
            TypeError: If wire_format is KAFKA_HEADERS (use serialize() instead).
            ResolverError: If the artifact_resolver raises or returns something other
                than a non-empty str.
            SchemaNotFoundError: If the resolved artifact does not exist in the registry.
            RegistryConnectionError: If the registry is unreachable.
            SerializationError: If the to_dict callable raises an exception.
            ValueError: If data does not conform to the Avro schema.
        """
        if self.wire_format is WireFormat.KAFKA_HEADERS:
            raise TypeError(
                "KAFKA_HEADERS wire format requires headers; "
                "use serialize() instead of calling the serializer directly."
            )
        return self.serialize(data, ctx).payload
