# Quickstart

This guide walks you through serializing your first Kafka message using `apicurio-serdes`.

## Prerequisites

- Apicurio Registry running and accessible (see [Installation](installation.md))
- A schema registered in the registry under a known `group_id` and `artifact_id`

For this guide, assume a registry at `http://localhost:8080/apis/registry/v3` with:

- Group: `com.example.schemas`
- Artifact: `UserEvent`
- Schema:

```json
{
  "type": "record",
  "name": "UserEvent",
  "fields": [
    {"name": "userId", "type": "string"},
    {"name": "country", "type": "string"}
  ]
}
```

## Step 1: Create a registry client

```python
from apicurio_serdes import ApicurioRegistryClient

client = ApicurioRegistryClient(
    url="http://localhost:8080/apis/registry/v3",
    group_id="com.example.schemas",
)
```

The client owns the connection to the registry and caches schemas after the first fetch — you only pay the HTTP cost once per artifact.

## Step 2: Create a serializer

```python
from apicurio_serdes.avro import AvroSerializer

serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
)
```

The serializer is bound to one schema artifact. Create one serializer per schema.

## Step 3: Serialize a message

```python
from apicurio_serdes.serialization import SerializationContext, MessageField

ctx = SerializationContext(topic="user-events", field=MessageField.VALUE)
payload: bytes = serializer({"userId": "abc-123", "country": "FR"}, ctx)
```

`payload` is now Confluent wire format bytes:

```
0x00  |  4-byte schema ID (big-endian)  |  Avro binary payload
```

## Step 4: Handle errors

```python
from apicurio_serdes._errors import SchemaNotFoundError, RegistryConnectionError, SerializationError

try:
    payload = serializer(data, ctx)
except SchemaNotFoundError as e:
    print(f"Schema not found: group={e.group_id}, artifact={e.artifact_id}")
except RegistryConnectionError as e:
    print(f"Registry unreachable at {e.url}")
except SerializationError as e:
    print(f"to_dict hook failed: {e.cause}")
except ValueError as e:
    print(f"Data does not match schema: {e}")
```

## Next steps

- [Avro Serializer guide](../user-guide/avro-serializer.md) — custom `to_dict` hooks, wire format options, strict mode
- [API Reference](../api-reference/index.md) — full class and method documentation
