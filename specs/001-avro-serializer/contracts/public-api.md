# Public API Contract: Avro Serializer (Producer Side)

**Feature**: 001-avro-serializer | **Date**: 2026-03-06

## Module Structure

```
apicurio_serdes/
  __init__.py              → exports: ApicurioRegistryClient
  _client.py               → ApicurioRegistryClient implementation
  _errors.py               → SchemaNotFoundError
  serialization.py         → exports: SerializationContext, MessageField
  avro/
    __init__.py            → exports: AvroSerializer
    _serializer.py         → AvroSerializer implementation
```

## Import Paths (SC-004: mirrors confluent-kafka conventions)

```python
from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroSerializer
from apicurio_serdes.serialization import SerializationContext, MessageField
```

---

## ApicurioRegistryClient

**Module**: `apicurio_serdes._client` (re-exported from `apicurio_serdes`)

```python
class ApicurioRegistryClient:
    """HTTP client for the Apicurio Registry v3 native API.

    Handles schema retrieval by group_id / artifact_id with
    built-in caching. Thread-safe for read operations.

    Args:
        url: Base URL of the Apicurio Registry v3 API.
             Example: "http://registry:8080/apis/registry/v3"
        group_id: Schema group identifier. Applied to every
                  schema lookup made by this client instance.

    Raises:
        ValueError: If url or group_id is empty.
    """

    def __init__(self, url: str, group_id: str) -> None: ...

    def get_schema(self, artifact_id: str) -> CachedSchema:
        """Retrieve an Avro schema by artifact ID.

        Returns a cached result on subsequent calls for the same
        artifact_id (FR-006).

        Args:
            artifact_id: The artifact identifier within the configured group.

        Returns:
            CachedSchema with parsed schema and content_id.

        Raises:
            SchemaNotFoundError: If the artifact does not exist in the
                registry (HTTP 404). Includes group_id and artifact_id
                in the error message (FR-008).
            httpx.HTTPStatusError: For other HTTP error responses.
            httpx.ConnectError: If the registry is unreachable.
        """
        ...
```

---

## AvroSerializer

**Module**: `apicurio_serdes.avro._serializer` (re-exported from `apicurio_serdes.avro`)

```python
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

    Usage:
        >>> serializer = AvroSerializer(client, "UserEvent")
        >>> payload = serializer({"userId": "abc"}, ctx)
    """

    def __init__(
        self,
        registry_client: ApicurioRegistryClient,
        artifact_id: str,
        to_dict: Callable[[Any, SerializationContext], dict] | None = None,
    ) -> None: ...

    def __call__(self, data: Any, ctx: SerializationContext) -> bytes:
        """Serialize data to Confluent-framed Avro bytes.

        Output format (FR-003):
          Byte 0:    Magic byte 0x00
          Bytes 1-4: content_id as 4-byte big-endian unsigned int
          Bytes 5+:  Avro binary payload (schemaless encoding)

        Args:
            data: The data to serialize. Must be a dict (or convertible
                  via to_dict) conforming to the Avro schema.
            ctx: Serialization context with topic and field metadata.

        Returns:
            Confluent wire format bytes.

        Raises:
            SchemaNotFoundError: If the artifact_id does not exist.
            ValueError: If data does not conform to the Avro schema
                (e.g., missing required field).
        """
        ...
```

---

## SerializationContext

**Module**: `apicurio_serdes.serialization`

```python
class SerializationContext:
    """Carries Kafka metadata at serialization time.

    Mirrors confluent-kafka's SerializationContext interface (SC-004).

    Args:
        topic: The target Kafka topic name.
        field: Whether this datum is a message key or value.
    """

    topic: str
    field: MessageField

    def __init__(self, topic: str, field: MessageField) -> None: ...
```

---

## MessageField

**Module**: `apicurio_serdes.serialization`

```python
class MessageField(enum.Enum):
    """Identifies whether serialized data is a Kafka key or value.

    Mirrors confluent-kafka's MessageField enum (SC-004).
    """

    KEY = "key"
    VALUE = "value"
```

---

## Errors

**Module**: `apicurio_serdes._errors`

```python
class SchemaNotFoundError(Exception):
    """Raised when an artifact_id does not exist in the registry.

    Attributes:
        group_id: The group that was searched.
        artifact_id: The artifact that was not found.
    """

    def __init__(self, group_id: str, artifact_id: str) -> None: ...
```

---

## Wire Format Specification (FR-003)

```
Offset  Size  Description
------  ----  -----------
0       1     Magic byte: 0x00
1       4     Schema identifier: content_id as big-endian uint32
5       var   Avro binary payload (fastavro schemaless encoding)
```

Encoding:
```python
import struct
header = b'\x00' + struct.pack('>I', content_id)
# payload = fastavro schemaless_writer output
result = header + payload
```
