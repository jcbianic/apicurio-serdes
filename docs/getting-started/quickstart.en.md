# Quickstart

Serialize your first Kafka message with `apicurio-serdes` in five minutes.

## Prerequisites

- **Python 3.10+** installed
- **Apicurio Registry 3.x** running and accessible (see below for a local setup)
- A schema registered under a known `group_id` and `artifact_id`

### Local Registry Setup

If you don't have a registry available, start one locally with Docker:

```bash
docker run -it -p 8080:8080 quay.io/apicurio/apicurio-registry:latest
```

The v3 API is now available at `http://localhost:8080/apis/registry/v3`.

Register a test schema using the REST API:

```bash
curl -X POST "http://localhost:8080/apis/registry/v3/groups/com.example.schemas/artifacts" \
  -H "Content-Type: application/json" \
  -H "X-Registry-ArtifactId: UserEvent" \
  -H "X-Registry-ArtifactType: AVRO" \
  -d '{
    "content": "{\"type\":\"record\",\"name\":\"UserEvent\",\"fields\":[{\"name\":\"userId\",\"type\":\"string\"},{\"name\":\"country\",\"type\":\"string\"}]}",
    "references": []
  }'
```

## Step 1 — Install the Library

```bash
uv add apicurio-serdes
```

Verify the installation:

```python
from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroSerializer

print("apicurio-serdes is ready.")
```

## Step 2 — Create a Registry Client

```python
from apicurio_serdes import ApicurioRegistryClient

client = ApicurioRegistryClient(
    url="http://localhost:8080/apis/registry/v3",
    group_id="com.example.schemas",
)
```

The client connects to the Apicurio v3 API and caches schemas after the first fetch. You only pay the HTTP cost once per artifact.

`group_id` tells the client which schema group to use for every lookup. In Apicurio, schemas are organized under groups (similar to namespaces). See [Addressing Model](../concepts/addressing-model.md) for details.

## Step 3 — Create a Serializer

```python
from apicurio_serdes.avro import AvroSerializer

serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
)
```

Each serializer is bound to one schema artifact. Create one serializer per schema you need.

## Step 4 — Serialize a Message

```python
from apicurio_serdes.serialization import SerializationContext, MessageField

ctx = SerializationContext(topic="user-events", field=MessageField.VALUE)
payload: bytes = serializer({"userId": "abc-123", "country": "FR"}, ctx)

print(f"Serialized {len(payload)} bytes")
# Serialized 16 bytes
```

`payload` is now [Confluent wire format](../concepts/wire-format.md) bytes:

```text
Byte 0:      0x00               (magic byte)
Bytes 1–4:   schema ID          (big-endian uint32)
Bytes 5+:    Avro binary data   (schemaless encoding)
```

## Step 5 — Send to Kafka

Use any Kafka client. Here is an example with `confluent-kafka`:

```python
from confluent_kafka import Producer

producer = Producer({"bootstrap.servers": "localhost:9092"})
producer.produce("user-events", value=payload)
producer.flush()
```

## Full Working Script

```python
from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroSerializer
from apicurio_serdes.serialization import SerializationContext, MessageField

# Connect to the registry
client = ApicurioRegistryClient(
    url="http://localhost:8080/apis/registry/v3",
    group_id="com.example.schemas",
)

# Create a serializer for the UserEvent schema
serializer = AvroSerializer(registry_client=client, artifact_id="UserEvent")

# Serialize a message
ctx = SerializationContext(topic="user-events", field=MessageField.VALUE)
payload: bytes = serializer({"userId": "abc-123", "country": "FR"}, ctx)

print(f"Success! Serialized {len(payload)} bytes of Confluent-framed Avro.")
print(f"Magic byte: 0x{payload[0]:02x}")
print(f"Schema ID:  {int.from_bytes(payload[1:5], 'big')}")
```

## Next Steps

- [Avro Serializer](../user-guide/avro-serializer.md) — parameters, `to_dict` hooks, wire format options, strict mode
- [Error Handling](../how-to/error-handling.md) — what to do when things go wrong
- [Migration from confluent-kafka](../migration/from-confluent-kafka.md) — side-by-side API comparison
- [API Reference](../api-reference/index.md) — full class and method documentation
