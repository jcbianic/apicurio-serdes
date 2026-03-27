"""Avro deserializer with Confluent wire format parsing."""

from __future__ import annotations

import io
import struct
from typing import TYPE_CHECKING, Any

import fastavro

from apicurio_serdes._errors import DeserializationError, ResolverError

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Literal

    from apicurio_serdes._client import ApicurioRegistryClient
    from apicurio_serdes.avro._strategies import ArtifactResolver
    from apicurio_serdes.serialization import SerializationContext


class _BaseAvroDeserializer:
    """Shared initialisation and decode logic for sync and async deserializers."""

    def __init__(
        self,
        from_dict: Callable[[dict[str, Any], SerializationContext], Any] | None,
        use_id: Literal["globalId", "contentId"],
        reader_schema: dict[str, Any] | None,
        artifact_id: str | None = None,
        artifact_resolver: ArtifactResolver | None = None,
        use_latest_version: bool = False,
    ) -> None:
        if artifact_id is not None and artifact_resolver is not None:
            raise ValueError(
                "artifact_id and artifact_resolver are mutually exclusive."
            )
        has_artifact_source = artifact_id is not None or artifact_resolver is not None
        if use_latest_version and not has_artifact_source:
            raise ValueError(
                "use_latest_version=True requires artifact_id or artifact_resolver."
            )
        if use_latest_version and reader_schema is not None:
            raise ValueError(
                "use_latest_version and reader_schema are mutually exclusive."
            )
        if has_artifact_source and not use_latest_version:
            raise ValueError(
                "artifact_id and artifact_resolver require use_latest_version=True."
            )
        self.from_dict = from_dict
        self.use_id = use_id
        self._artifact_id = artifact_id
        self._artifact_resolver: ArtifactResolver | None = artifact_resolver
        self._resolved_artifact_id: str | None = None
        self._use_latest_version = use_latest_version
        self._parsed_cache: dict[int, Any] = {}
        self._parsed_reader_schema = (
            fastavro.parse_schema(reader_schema) if reader_schema is not None else None
        )

    def _resolve_artifact_id(self, ctx: SerializationContext) -> str:
        """Resolve artifact_id from static value or resolver, with caching."""
        if self._artifact_resolver is not None and self._resolved_artifact_id is None:
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
            self._artifact_id
            if self._artifact_id is not None
            else self._resolved_artifact_id
        )
        if effective_id is None:  # pragma: no cover
            raise RuntimeError(
                "artifact_id is None and no resolver produced an ID; "
                "this is an internal invariant violation."
            )
        return effective_id

    def _decode(
        self,
        schema_id: int,
        schema_dict: dict[str, Any],
        payload: bytes,
        ctx: SerializationContext,
    ) -> Any:
        """Cache the writer schema and decode the Avro payload."""
        # Cache parsed schema to avoid repeated parse_schema calls (FR-007)
        if schema_id not in self._parsed_cache:
            self._parsed_cache[schema_id] = fastavro.parse_schema(schema_dict)
        parsed_schema = self._parsed_cache[schema_id]

        # FR-011: decode Avro payload
        try:
            result: Any = fastavro.schemaless_reader(
                io.BytesIO(payload), parsed_schema, self._parsed_reader_schema
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


class AvroDeserializer(_BaseAvroDeserializer):
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
        from apicurio_serdes import ApicurioRegistryClient
        from apicurio_serdes.avro import AvroDeserializer
        from apicurio_serdes.serialization import SerializationContext, MessageField

        client = ApicurioRegistryClient(
            url="http://localhost:8080/apis/registry/v3",
            group_id="com.example.schemas",
        )
        # Dynamically use the latest registry schema as the reader schema:
        deserializer = AvroDeserializer(
            registry_client=client,
            artifact_id="UserEvent",
            use_latest_version=True,
        )
        ctx = SerializationContext(topic="user-events", field=MessageField.VALUE)
        result = deserializer(raw_bytes, ctx)
        ```
    """

    def __init__(
        self,
        registry_client: ApicurioRegistryClient,
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
            ResolverError: If ``use_latest_version=True`` with an
                ``artifact_resolver`` and the resolver raises or returns
                a non-string value.
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

        if self._use_latest_version and self._parsed_reader_schema is None:
            effective_id = self._resolve_artifact_id(ctx)
            cached = self.registry_client.get_schema(effective_id)
            self._parsed_reader_schema = fastavro.parse_schema(cached.schema)

        return self._decode(schema_id, schema_dict, data[5:], ctx)
