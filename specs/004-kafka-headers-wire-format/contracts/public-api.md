# Public API Contract: WireFormat.KAFKA_HEADERS Support

**Feature**: 004-kafka-headers-wire-format | **Date**: 2026-03-06
**Extends**: `specs/001-avro-serializer/contracts/public-api.md`

---

## Updated Module Structure

```
apicurio_serdes/
  __init__.py              → exports: ApicurioRegistryClient, WireFormat (NEW)
  _client.py               → (unchanged)
  _errors.py               → (unchanged)
  serialization.py         → exports: SerializationContext, MessageField,
                                       WireFormat (NEW), SerializedMessage (NEW)
  avro/
    __init__.py            → exports: AvroSerializer (updated)
    _serializer.py         → AvroSerializer implementation (updated)
```

## Updated Import Paths

```python
# Existing — unchanged
from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroSerializer
from apicurio_serdes.serialization import SerializationContext, MessageField

# New (FR-002, SC-004)
from apicurio_serdes import WireFormat
from apicurio_serdes.serialization import WireFormat, SerializedMessage
```

---

## WireFormat

**Module**: `apicurio_serdes.serialization` (re-exported from `apicurio_serdes`)

```python
class WireFormat(enum.Enum):
    """Selects the wire format framing for an AvroSerializer.

    Members:
        CONFLUENT_PAYLOAD: Default. Schema identifier embedded in message bytes
            as a magic byte (0x00) + 4-byte big-endian uint32 prefix.
        KAFKA_HEADERS: Schema identifier communicated as a Kafka message header.
            Message bytes contain only the raw Avro binary payload.
    """

    CONFLUENT_PAYLOAD = "CONFLUENT_PAYLOAD"
    KAFKA_HEADERS = "KAFKA_HEADERS"
```

---

## SerializedMessage

**Module**: `apicurio_serdes.serialization`

```python
@dataclass(frozen=True)
class SerializedMessage:
    """Result of AvroSerializer.serialize().

    Carries the serialized payload bytes and any Kafka message headers
    produced by the chosen wire format mode.

    Attributes:
        payload: The serialized message body.
            For CONFLUENT_PAYLOAD: framed bytes (magic byte + 4-byte ID + Avro).
            For KAFKA_HEADERS: raw Avro binary only (no prefix).
        headers: Kafka message headers to attach to the produced record.
            For CONFLUENT_PAYLOAD: always empty dict {}.
            For KAFKA_HEADERS: one entry {header_name: header_value} where
            header_name follows Apicurio's native naming convention and
            header_value is the schema ID encoded as 8-byte big-endian signed long.
    """

    payload: bytes
    headers: dict[str, bytes]
```

---

## AvroSerializer (updated)

**Module**: `apicurio_serdes.avro._serializer` (re-exported from `apicurio_serdes.avro`)

```python
class AvroSerializer:
    """Serializes Python data to Avro bytes with configurable wire format framing.

    Fetches the Avro schema from the registry on first call and caches it.

    Args:
        registry_client: An ApicurioRegistryClient instance.
        artifact_id: The artifact identifier for the target schema.
        to_dict: Optional callable that converts input data to a dict
                 before Avro encoding. Signature: (data, ctx) -> dict.
                 When None, input is passed directly to the encoder.
        use_id: Which registry-assigned identifier to use as the schema ID.
                "globalId" (default) or "contentId". Applies to both wire
                format modes.
        strict: When True, reject extra fields not in the schema.
        wire_format: The wire format framing mode. Defaults to
                     WireFormat.CONFLUENT_PAYLOAD (FR-003).
    """

    def __init__(
        self,
        registry_client: ApicurioRegistryClient,
        artifact_id: str,
        to_dict: Callable[[Any, SerializationContext], dict[str, Any]] | None = None,
        use_id: Literal["globalId", "contentId"] = "globalId",
        strict: bool = False,
        wire_format: WireFormat = WireFormat.CONFLUENT_PAYLOAD,
    ) -> None: ...

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
            SchemaNotFoundError: If artifact_id does not exist in the registry.
            RegistryConnectionError: If the registry is unreachable.
            SerializationError: If the to_dict callable raises an exception.
            ValueError: If data does not conform to the Avro schema.
        """
        ...

    def __call__(self, data: Any, ctx: SerializationContext) -> bytes:
        """Serialize data to bytes. Delegates to serialize() and returns payload.

        For CONFLUENT_PAYLOAD: returns framed bytes — identical to pre-feature
        behavior. For KAFKA_HEADERS: returns raw Avro binary bytes only;
        headers are discarded. Use serialize() when headers are needed.

        Args:
            data: The data to serialize.
            ctx: Serialization context.

        Returns:
            Serialized bytes (payload only).

        Raises:
            SchemaNotFoundError, RegistryConnectionError, SerializationError,
            ValueError — same conditions as serialize().
        """
        ...
```

---

## Wire Format Specifications

### CONFLUENT_PAYLOAD (FR-004 — unchanged)

```
Offset  Size  Description
------  ----  -----------
0       1     Magic byte: 0x00
1       4     Schema identifier: big-endian uint32 (globalId or contentId)
5       var   Avro binary payload (fastavro schemaless encoding)
```

```python
header = b"\x00" + struct.pack(">I", schema_id)
payload = fastavro_schemaless_writer_output
result = header + payload
```

### KAFKA_HEADERS (FR-005, FR-006, FR-007 — new)

**Payload** (message body — no framing):
```
Offset  Size  Description
------  ----  -----------
0       var   Avro binary payload (fastavro schemaless encoding — no prefix)
```

**Header** (one Kafka message header):
```
Header name:  see table below
Header value: 8-byte big-endian signed int64 (schema ID)
```

Header name lookup:

| MessageField | use_id | Header name |
|---|---|---|
| VALUE | "globalId" | `apicurio.value.globalId` |
| VALUE | "contentId" | `apicurio.value.contentId` |
| KEY | "globalId" | `apicurio.key.globalId` |
| KEY | "contentId" | `apicurio.key.contentId` |

Header value encoding:
```python
header_value = struct.pack(">q", schema_id)  # 8-byte big-endian signed int64
# Matches Java: ByteBuffer.allocate(8).putLong(globalId).array()
```
