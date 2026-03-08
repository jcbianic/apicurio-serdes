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
pip install apicurio-serdes
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

The client connects to the Apicurio v3 API and caches schemas after the first fetch — you only pay the HTTP cost once per artifact.

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
# Serialized 19 bytes
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

## Troubleshooting

### Wrong Registry URL

**Error**: `RegistryConnectionError: Unable to connect to registry at http://wrong-host:8080/...: ...`

**Cause**: The `url` parameter does not point to a running Apicurio Registry.

**Fix**: Verify the registry is running and the URL includes the full v3 API path:

```python
# Correct — includes /apis/registry/v3
client = ApicurioRegistryClient(
    url="http://localhost:8080/apis/registry/v3",
    group_id="com.example.schemas",
)

# Wrong — missing API path
client = ApicurioRegistryClient(
    url="http://localhost:8080",  # Will fail!
    group_id="com.example.schemas",
)
```

### Non-existent Artifact

**Error**: `SchemaNotFoundError: Schema not found: artifact 'MySchema' in group 'default'`

**Cause**: The `artifact_id` does not exist in the specified group, or the `group_id` is wrong.

**Fix**: Check that the schema exists in the registry under the correct group:

```bash
# List artifacts in a group
curl "http://localhost:8080/apis/registry/v3/groups/com.example.schemas/artifacts"
```

Common mistakes:

- The schema is in a different group than the one you specified
- The artifact ID is case-sensitive — `UserEvent` is not the same as `userevent`
- The schema was registered in the `default` group but you are looking in a named group

### Invalid Input Data

**Error**: `ValueError: ... is not a valid ...` (from fastavro)

**Cause**: The data dictionary does not match the Avro schema — a required field is missing, a field has the wrong type, or the data structure does not match the schema's expected shape.

**Fix**: Verify that your data matches the schema exactly:

```python
# Schema expects: {"userId": string, "country": string}

# Correct
serializer({"userId": "abc", "country": "FR"}, ctx)

# Wrong — missing required field "country"
serializer({"userId": "abc"}, ctx)

# Wrong — "userId" should be a string, not an int
serializer({"userId": 123, "country": "FR"}, ctx)
```

## Next Steps

- [Avro Serializer Guide](../user-guide/avro-serializer.md) — custom `to_dict` hooks, wire format options, strict mode
- [Migration from confluent-kafka](../migration/from-confluent-kafka.md) — side-by-side API comparison
- [API Reference](../api-reference/index.md) — full class and method documentation
