# Quickstart: WireFormat.KAFKA_HEADERS Support

**Feature**: 004-kafka-headers-wire-format | **Date**: 2026-03-06

---

## Setup

No new dependencies are required. The `WireFormat` enum and `SerializedMessage` dataclass are added to the existing library.

```python
from apicurio_serdes import ApicurioRegistryClient, WireFormat
from apicurio_serdes.avro import AvroSerializer
from apicurio_serdes.serialization import SerializationContext, MessageField
```

---

## Scenario 1: KAFKA_HEADERS mode (new)

Produce a message where the schema ID is carried in Kafka message headers rather than embedded in the bytes.

```python
client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="com.example.schemas",
)

serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    wire_format=WireFormat.KAFKA_HEADERS,  # FR-003
)

ctx = SerializationContext(topic="user-events", field=MessageField.VALUE)

# Use serialize() to get both payload bytes and headers (FR-010 Option C)
result = serializer.serialize({"userId": "abc", "country": "FR"}, ctx)

# result.payload: raw Avro binary — no magic byte, no schema ID prefix (FR-005)
# result.headers: {"apicurio.registry.globalId": b"\x00\x00\x00\x00\x00\x00\x00\x01"} (FR-006, FR-007)

# Pass to confluent-kafka producer:
producer.produce(
    topic=ctx.topic,
    value=result.payload,
    headers=list(result.headers.items()),
)
```

---

## Scenario 2: KAFKA_HEADERS with KEY field

When serializing a Kafka message key, the header name uses the `key.` prefix.

```python
serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserKey",
    wire_format=WireFormat.KAFKA_HEADERS,
)

ctx = SerializationContext(topic="user-events", field=MessageField.KEY)
result = serializer.serialize({"userId": "abc"}, ctx)

# result.headers key: "apicurio.registry.key.globalId"
```

---

## Scenario 3: KAFKA_HEADERS with contentId

When `use_id="contentId"`, the header name changes accordingly.

```python
serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    use_id="contentId",
    wire_format=WireFormat.KAFKA_HEADERS,
)

ctx = SerializationContext(topic="user-events", field=MessageField.VALUE)
result = serializer.serialize({"userId": "abc", "country": "FR"}, ctx)

# result.headers key: "apicurio.registry.contentId"
# result.headers value: struct.pack(">q", content_id)  — 8 bytes
```

---

## Scenario 4: CONFLUENT_PAYLOAD (unchanged default)

Existing code continues to work without modification. No `wire_format` argument needed.

```python
# Unchanged API — no wire_format argument (US2, SC-003)
serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
)

ctx = SerializationContext(topic="user-events", field=MessageField.VALUE)
payload = serializer({"userId": "abc", "country": "FR"}, ctx)
# payload[0:1] == b"\x00"  — magic byte (FR-004)
# struct.unpack(">I", payload[1:5])[0] == global_id  — 4-byte ID
```

Explicit `wire_format=WireFormat.CONFLUENT_PAYLOAD` produces identical output:

```python
serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    wire_format=WireFormat.CONFLUENT_PAYLOAD,
)
# Produces same bytes as above (US2 scenario 2)
```

---

## Scenario 5: Using `serialize()` with CONFLUENT_PAYLOAD

`serialize()` works for both modes. For CONFLUENT_PAYLOAD, headers is always empty.

```python
result = serializer.serialize({"userId": "abc", "country": "FR"}, ctx)
# result.payload == serializer({"userId": "abc", "country": "FR"}, ctx)  — identical bytes
# result.headers == {}
```

---

## Schema Caching (SC-005, NFR-001)

Schema caching is preserved across both wire format modes. The cache key is `(group_id, artifact_id)` — identical to CONFLUENT_PAYLOAD mode.

```python
# Only 1 HTTP call regardless of message count or wire_format setting
for record in records:  # e.g., 1000 records
    result = serializer.serialize(record, ctx)
```

---

## Header Value Decoding Reference

To verify byte-level interoperability with Apicurio Java serde:

```python
import struct

# Encode (Python → Kafka header value)
header_value = struct.pack(">q", schema_id)  # 8 bytes

# Decode (Kafka header value → Python)
(schema_id,) = struct.unpack(">q", header_value)

# Java equivalent: ByteBuffer.wrap(headerBytes).getLong()
```
