"""Avro serializer with Confluent wire format framing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Literal

    from apicurio_serdes._client import ApicurioRegistryClient
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

    def __call__(self, data: Any, ctx: SerializationContext) -> bytes:
        """Serialize data to Confluent-framed Avro bytes."""
        raise NotImplementedError
