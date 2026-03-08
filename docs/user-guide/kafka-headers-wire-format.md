# KAFKA_HEADERS Wire Format Mode

The `WireFormat.KAFKA_HEADERS` mode allows you to produce Avro messages where
the schema identifier is carried in Kafka message headers rather than embedded
in the message bytes. This is an important deployment pattern in Apicurio
Registry setups that prefer payload-clean messages with out-of-band schema
identification.

In contrast to the default `CONFLUENT_PAYLOAD` mode (which prepends a magic
byte and 4-byte schema ID to the payload), `KAFKA_HEADERS` produces raw Avro
binary as the message body and communicates the schema identifier via a
dedicated Kafka header.

## Setup

No additional dependencies are required. All the necessary classes are part of
the core library.

```python
from apicurio_serdes import ApicurioRegistryClient, WireFormat
from apicurio_serdes.avro import AvroSerializer
from apicurio_serdes.serialization import SerializationContext, MessageField
```

Create a registry client as usual:

```python
client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="com.example.schemas",
)
```

## Usage

### Serializing with KAFKA_HEADERS

Pass `wire_format=WireFormat.KAFKA_HEADERS` when constructing the serializer,
then use the `serialize()` method to get both the payload bytes and the Kafka
headers:

```python
serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    wire_format=WireFormat.KAFKA_HEADERS,
)

ctx = SerializationContext(topic="user-events", field=MessageField.VALUE)

result = serializer.serialize({"userId": "abc", "country": "FR"}, ctx)

# result.payload  -> raw Avro binary (no magic byte, no schema ID prefix)
# result.headers  -> {"apicurio.value.globalId": b"\x00\x00\x00\x00\x00\x00\x00\x01"}

# Pass both to your Kafka producer:
producer.produce(
    topic=ctx.topic,
    value=result.payload,
    headers=list(result.headers.items()),
)
```

The `serialize()` method returns a `SerializedMessage` dataclass with two
fields:

- **`payload`** (`bytes`): The raw Avro binary data -- no framing prefix.
- **`headers`** (`dict[str, bytes]`): A single-entry dict with the schema
  identifier header.

### Serializing a Kafka KEY

When serializing a message key, use `MessageField.KEY` in the serialization
context. The header name automatically uses the `key` prefix:

```python
serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserKey",
    wire_format=WireFormat.KAFKA_HEADERS,
)

ctx = SerializationContext(topic="user-events", field=MessageField.KEY)
result = serializer.serialize({"userId": "abc"}, ctx)

# result.headers key is "apicurio.key.globalId"
```

### Using contentId instead of globalId

By default, the header carries the `globalId`. Pass `use_id="contentId"` to
use the content identifier instead:

```python
serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    use_id="contentId",
    wire_format=WireFormat.KAFKA_HEADERS,
)

ctx = SerializationContext(topic="user-events", field=MessageField.VALUE)
result = serializer.serialize({"userId": "abc", "country": "FR"}, ctx)

# result.headers key is "apicurio.value.contentId"
```

### CONFLUENT_PAYLOAD default is unchanged

Existing code continues to work without modification. The default wire format
remains `WireFormat.CONFLUENT_PAYLOAD`:

```python
# No wire_format argument -- uses CONFLUENT_PAYLOAD by default
serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
)

ctx = SerializationContext(topic="user-events", field=MessageField.VALUE)
payload = serializer({"userId": "abc", "country": "FR"}, ctx)

# payload[0:1] == b"\x00"           (magic byte)
# payload[1:5]                       (4-byte big-endian schema ID)
# payload[5:]                        (Avro binary data)
```

Passing `wire_format=WireFormat.CONFLUENT_PAYLOAD` explicitly produces
identical output. The `serialize()` method works for both modes -- for
CONFLUENT_PAYLOAD, `result.headers` is always an empty dict:

```python
result = serializer.serialize({"userId": "abc", "country": "FR"}, ctx)
# result.payload == serializer({"userId": "abc", "country": "FR"}, ctx)
# result.headers == {}
```

## Header Format Reference

The header name follows Apicurio Registry's native naming convention,
combining the message field type and the identifier kind:

| MessageField | use_id       | Header name                  | Header value encoding                |
|:-------------|:-------------|:-----------------------------|:-------------------------------------|
| VALUE        | `"globalId"` | `apicurio.value.globalId`    | `struct.pack(">q", global_id)` -- 8 bytes |
| VALUE        | `"contentId"`| `apicurio.value.contentId`   | `struct.pack(">q", content_id)` -- 8 bytes |
| KEY          | `"globalId"` | `apicurio.key.globalId`      | `struct.pack(">q", global_id)` -- 8 bytes |
| KEY          | `"contentId"`| `apicurio.key.contentId`     | `struct.pack(">q", content_id)` -- 8 bytes |

## Header Value Encoding

The schema identifier is encoded as an **8-byte big-endian signed long**
(`struct.pack(">q", schema_id)`). This matches the encoding used by Apicurio
Registry's native Java KAFKA_HEADERS serde, ensuring byte-level
interoperability.

```python
import struct

# Encode (Python -> Kafka header value)
header_value = struct.pack(">q", schema_id)  # 8 bytes

# Decode (Kafka header value -> Python)
(schema_id,) = struct.unpack(">q", header_value)

# Java equivalent: ByteBuffer.wrap(headerBytes).getLong()
```

## Schema Caching

Schema caching is fully preserved in KAFKA_HEADERS mode. The cache key is
`(group_id, artifact_id)`, identical to CONFLUENT_PAYLOAD mode. Regardless of
message count or wire format setting, only **one HTTP call** is made to the
registry per unique artifact:

```python
# 1 HTTP call regardless of message count or wire_format
for record in records:
    result = serializer.serialize(record, ctx)
```

## Further Reading

- Quickstart examples: `specs/004-kafka-headers-wire-format/quickstart.md`
- Feature specification: `specs/004-kafka-headers-wire-format/spec.md`
- API reference: auto-generated from docstrings in
  `apicurio_serdes.serialization` and `apicurio_serdes.avro`
