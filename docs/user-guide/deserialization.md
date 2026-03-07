# Deserialization

Deserialize Confluent-framed Avro bytes from Kafka into Python dicts
using `AvroDeserializer` and the Apicurio Registry.

## Basic Usage

```python
from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroDeserializer
from apicurio_serdes.serialization import SerializationContext, MessageField

client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="my-group",
)

deserializer = AvroDeserializer(client)

ctx = SerializationContext("my-topic", MessageField.VALUE)
record = deserializer(kafka_message.value(), ctx)
# record is a Python dict: {"userId": "abc123", "country": "FR"}
```

## Round-Trip (Serialize + Deserialize)

```python
from apicurio_serdes.avro import AvroSerializer, AvroDeserializer

# Serialize
serializer = AvroSerializer(client, "UserEvent", use_id="contentId")
ctx = SerializationContext("events", MessageField.VALUE)
payload = serializer({"userId": "abc123", "country": "FR"}, ctx)

# Deserialize (use_id must match the serializer)
deserializer = AvroDeserializer(client, use_id="contentId")
result = deserializer(payload, ctx)

assert result == {"userId": "abc123", "country": "FR"}
```

**Important**: The `use_id` parameter must match on both serializer and
deserializer. If the serializer embeds a `globalId`, the deserializer must
interpret it as a `globalId`.

## Custom Object Transformation

Use `from_dict` to automatically convert decoded dicts into domain objects:

```python
from dataclasses import dataclass

@dataclass
class UserEvent:
    user_id: str
    country: str

def from_dict(d: dict, ctx: SerializationContext) -> UserEvent:
    return UserEvent(user_id=d["userId"], country=d["country"])

deserializer = AvroDeserializer(client, from_dict=from_dict)
event = deserializer(payload, ctx)
# event is a UserEvent instance, not a plain dict
```

## Error Handling

```python
from apicurio_serdes._errors import (
    DeserializationError,
    RegistryConnectionError,
    SchemaNotFoundError,
)

try:
    result = deserializer(payload, ctx)
except DeserializationError as e:
    # Bad magic byte, too few bytes, decode failure, or from_dict failure
    print(f"Deserialization failed: {e}")
    if e.__cause__:
        print(f"Caused by: {e.__cause__}")
except SchemaNotFoundError as e:
    # Schema ID from wire format not found in registry
    print(f"Unknown schema: {e}")
except RegistryConnectionError as e:
    # Registry unreachable
    print(f"Registry error: {e}")
```

### Error Types

| Error | When |
|-------|------|
| `DeserializationError` | Invalid magic byte, input < 5 bytes, Avro decode failure, `from_dict` exception |
| `SchemaNotFoundError` | Schema ID in wire format not found in registry (HTTP 404) |
| `RegistryConnectionError` | Registry unreachable during schema resolution |

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `registry_client` | (required) | `ApicurioRegistryClient` instance |
| `from_dict` | `None` | Optional `(dict, ctx) -> Any` transformation |
| `use_id` | `"contentId"` | Which ID type the wire format field represents |

## Schema Caching

Schemas resolved during deserialization are cached by the client. Repeated
deserialization of messages sharing the same schema identifier results in
exactly one registry HTTP call. The cache is thread-safe.
