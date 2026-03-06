# Data Model: WireFormat.KAFKA_HEADERS Support

**Feature**: 004-kafka-headers-wire-format | **Date**: 2026-03-06

---

## New Entities

### WireFormat

**Module**: `apicurio_serdes.serialization`
**Type**: `enum.Enum`

Selects the wire format mode for an `AvroSerializer` instance. Controls whether the schema identifier is embedded in the message bytes (`CONFLUENT_PAYLOAD`) or communicated via Kafka message headers (`KAFKA_HEADERS`).

```python
class WireFormat(enum.Enum):
    CONFLUENT_PAYLOAD = "CONFLUENT_PAYLOAD"
    KAFKA_HEADERS = "KAFKA_HEADERS"
```

| Member | Value | Behavior |
|--------|-------|----------|
| `CONFLUENT_PAYLOAD` | `"CONFLUENT_PAYLOAD"` | Default. Produces `0x00` + 4-byte uint32 schema ID + Avro payload. |
| `KAFKA_HEADERS` | `"KAFKA_HEADERS"` | Produces raw Avro payload only; schema ID communicated as a Kafka message header. |

**Constraints**:
- Only these two members are valid. Passing an invalid value raises `ValueError` at construction time (Python enum enforcement).
- This enum is the only configuration point for wire format selection.

---

### SerializedMessage

**Module**: `apicurio_serdes.serialization`
**Type**: `dataclasses.dataclass(frozen=True)`

Return type of `AvroSerializer.serialize()`. Carries both the serialized payload bytes and any associated Kafka message headers.

```python
@dataclass(frozen=True)
class SerializedMessage:
    payload: bytes
    headers: dict[str, bytes]
```

| Field | Type | Description |
|-------|------|-------------|
| `payload` | `bytes` | The serialized message body. For `CONFLUENT_PAYLOAD`: framed bytes (`0x00` + 4-byte ID + Avro). For `KAFKA_HEADERS`: raw Avro binary only. |
| `headers` | `dict[str, bytes]` | Kafka message headers. For `CONFLUENT_PAYLOAD`: always `{}`. For `KAFKA_HEADERS`: one entry `{header_name: header_value}` where `header_value` is 8 bytes. |

**Constraints**:
- `payload` is never empty for a successful serialization.
- `headers` has exactly 0 entries for CONFLUENT_PAYLOAD and exactly 1 entry for KAFKA_HEADERS.
- Immutable (`frozen=True`): callers must not mutate the instance.

---

## Modified Entities

### AvroSerializer (updated)

**Module**: `apicurio_serdes.avro._serializer`

One new constructor parameter; one new method; `__call__` delegates to `serialize()`.

#### New constructor parameter

```
wire_format: WireFormat = WireFormat.CONFLUENT_PAYLOAD
```

Selects the framing strategy. Defaults to `WireFormat.CONFLUENT_PAYLOAD` (unchanged behavior for existing callers).

#### New method: `serialize()`

```
serialize(data: Any, ctx: SerializationContext) -> SerializedMessage
```

Serializes `data` and returns both payload bytes and any associated headers. For CONFLUENT_PAYLOAD, `headers` is `{}`. For KAFKA_HEADERS, `payload` is raw Avro binary and `headers` contains exactly one entry.

**Error behaviour** (identical to `__call__`):
- `SchemaNotFoundError` if artifact does not exist — no payload, no headers returned.
- `RegistryConnectionError` if registry unreachable.
- `SerializationError` if `to_dict` hook raises.
- `ValueError` if data does not conform to schema (strict mode or fastavro validation).

#### Updated `__call__`

```
__call__(data: Any, ctx: SerializationContext) -> bytes
```

Delegates to `serialize()` and returns `.payload`. Return type is unchanged. Existing callers of `__call__` in CONFLUENT_PAYLOAD mode see zero behavioral change. Callers in KAFKA_HEADERS mode who use `__call__` receive the raw Avro payload bytes; headers are discarded (callers who need headers must use `serialize()`).

---

## State Transitions

```
AvroSerializer construction
    │
    ├─ wire_format = CONFLUENT_PAYLOAD (default)
    │      │
    │      └─ serialize() / __call__()
    │              │
    │              └─ SerializedMessage(payload=framed_bytes, headers={})
    │
    └─ wire_format = KAFKA_HEADERS
           │
           └─ serialize()
                   │
                   └─ SerializedMessage(payload=raw_avro_bytes, headers={name: 8_bytes})
```

---

## KAFKA_HEADERS Header Specification

The single header entry in `headers` for KAFKA_HEADERS mode:

| `ctx.field` | `use_id` | Header name | Header value |
|---|---|---|---|
| `MessageField.VALUE` | `"globalId"` | `"apicurio.registry.globalId"` | `struct.pack(">q", global_id)` |
| `MessageField.VALUE` | `"contentId"` | `"apicurio.registry.contentId"` | `struct.pack(">q", content_id)` |
| `MessageField.KEY` | `"globalId"` | `"apicurio.registry.key.globalId"` | `struct.pack(">q", global_id)` |
| `MessageField.KEY` | `"contentId"` | `"apicurio.registry.key.contentId"` | `struct.pack(">q", content_id)` |

Header value encoding: 8-byte big-endian signed integer (`struct.pack(">q", ...)`) — byte-level compatible with Apicurio Registry's Java `DefaultHeadersHandler` (`ByteBuffer.putLong()`, big-endian default).
