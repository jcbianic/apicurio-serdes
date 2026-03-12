# Public API Contract: Avro Deserializer (Consumer Side)

**Feature**: 002-avro-deserializer | **Date**: 2026-03-06

## Module Structure (updated)

```
apicurio_serdes/
  __init__.py              -> exports: ApicurioRegistryClient
  _client.py               -> ApicurioRegistryClient implementation (+ new ID-based methods)
  _errors.py               -> SchemaNotFoundError (+ from_id), SerializationError,
                              DeserializationError (NEW), RegistryConnectionError
  serialization.py         -> exports: SerializationContext, MessageField
  avro/
    __init__.py            -> exports: AvroSerializer, AvroDeserializer (NEW)
    _serializer.py         -> AvroSerializer implementation
    _deserializer.py       -> AvroDeserializer implementation (NEW)
```

## Import Paths (SC-004: mirrors confluent-kafka conventions)

```python
from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroDeserializer
from apicurio_serdes.serialization import SerializationContext, MessageField
from apicurio_serdes._errors import DeserializationError
```

---

## AvroDeserializer (NEW)

**Module**: `apicurio_serdes.avro._deserializer` (re-exported from `apicurio_serdes.avro`)

```python
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
                setting. Defaults to "globalId" (FR-006, ADR-006).

    Usage:
        >>> deserializer = AvroDeserializer(client)
        >>> record = deserializer(payload, ctx)
    """

    def __init__(
        self,
        registry_client: ApicurioRegistryClient,
        from_dict: Callable[[dict, SerializationContext], Any] | None = None,
        use_id: Literal["globalId", "contentId"] = "globalId",
    ) -> None: ...

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
        ...
```

---

## ApicurioRegistryClient (extended)

**Module**: `apicurio_serdes._client` (re-exported from `apicurio_serdes`)

New methods added alongside existing `get_schema`:

```python
class ApicurioRegistryClient:
    # ... existing __init__ and get_schema unchanged ...

    def get_schema_by_global_id(self, global_id: int) -> dict[str, Any]:
        """Retrieve an Avro schema by its globalId.

        Returns a cached result on subsequent calls for the same
        globalId (FR-007).

        Args:
            global_id: The globalId from the wire format header.

        Returns:
            Parsed Avro schema as a Python dict.

        Raises:
            SchemaNotFoundError: If no schema exists for this globalId
                (HTTP 404). Includes the id_type and id_value in the
                error message (FR-010).
            RegistryConnectionError: If the registry is unreachable (FR-012).
        """
        ...

    def get_schema_by_content_id(self, content_id: int) -> dict[str, Any]:
        """Retrieve an Avro schema by its contentId.

        Returns a cached result on subsequent calls for the same
        contentId (FR-007).

        Args:
            content_id: The contentId from the wire format header.

        Returns:
            Parsed Avro schema as a Python dict.

        Raises:
            SchemaNotFoundError: If no schema exists for this contentId
                (HTTP 404). Includes the id_type and id_value in the
                error message (FR-010).
            RegistryConnectionError: If the registry is unreachable (FR-012).
        """
        ...
```

---

## DeserializationError (NEW)

**Module**: `apicurio_serdes._errors`

```python
class DeserializationError(Exception):
    """Raised when deserialization fails.

    Covers: invalid magic byte (FR-003), input too short (FR-004),
    Avro decode failure (FR-011), and from_dict hook failure (FR-009).

    When wrapping an underlying exception, the original is set as
    __cause__ to preserve the full traceback.

    Attributes:
        message: Descriptive error message.
    """

    def __init__(self, message: str, cause: Exception | None = None) -> None: ...
```

---

## SchemaNotFoundError (extended)

**Module**: `apicurio_serdes._errors`

New classmethod added alongside existing `__init__`:

```python
class SchemaNotFoundError(Exception):
    # ... existing __init__(group_id, artifact_id) unchanged ...

    @classmethod
    def from_id(cls, id_type: str, id_value: int) -> SchemaNotFoundError:
        """Create a SchemaNotFoundError for an ID-based lookup failure.

        Args:
            id_type: "globalId" or "contentId".
            id_value: The numeric identifier that was not found.

        Returns:
            A SchemaNotFoundError with a descriptive message and
            id_type/id_value attributes.
        """
        ...
```

---

## Wire Format Specification (read direction)

```
Offset  Size  Description
------  ----  -----------
0       1     Magic byte: must be 0x00
1       4     Schema identifier: globalId or contentId -- big-endian uint32
5       var   Avro binary payload (fastavro schemaless encoding)
```

Decoding:
```python
import struct

magic = data[0]         # must be 0x00
schema_id = struct.unpack(">I", data[1:5])[0]
avro_payload = data[5:]  # remaining bytes
```

The `use_id` parameter determines how to interpret `schema_id`:
- `"globalId"` -> call `client.get_schema_by_global_id(schema_id)`
- `"contentId"` -> call `client.get_schema_by_content_id(schema_id)`
