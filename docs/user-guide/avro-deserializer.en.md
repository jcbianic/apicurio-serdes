# Avro Deserializer

`AvroDeserializer` reads Confluent wire-format bytes, resolves the embedded schema identifier against the Apicurio Registry, and returns a Python dict (or a domain object when a `from_dict` hook is configured).

## Basic usage

```python
from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroDeserializer
from apicurio_serdes.serialization import SerializationContext, MessageField

client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="com.example.schemas",
)

deserializer = AvroDeserializer(client)

ctx = SerializationContext("my-topic", MessageField.VALUE)
record = deserializer(kafka_message.value(), ctx)
# record is a Python dict: {"userId": "abc123", "country": "FR"}
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `registry_client` | `ApicurioRegistryClient` | required | The registry client used to resolve schema identifiers. |
| `from_dict` | callable | `None` | Optional `(dict, ctx) -> Any` transformation applied after decoding. |
| `use_id` | `"contentId"` or `"globalId"` | `"globalId"` | How to interpret the 4-byte schema identifier in the wire format header. |

### Schema identifier mode (`use_id`)

The Confluent wire format stores a 4-byte schema identifier in bytes 1–4. The `use_id` parameter controls how that integer is resolved against the registry:

| `use_id` | Registry endpoint |
|----------|-------------------|
| `"globalId"` (default) | `GET /ids/globalIds/{id}` |
| `"contentId"` | `GET /ids/contentIds/{id}` |

**Important**: `use_id` must match the value used by the producer. If the producer embedded a `globalId`, the deserializer must use `use_id="globalId"`.

## Round-trip with AvroSerializer

```python
from apicurio_serdes.avro import AvroSerializer, AvroDeserializer

serializer = AvroSerializer(client, "UserEvent", use_id="contentId")
deserializer = AvroDeserializer(client, use_id="contentId")

ctx = SerializationContext("events", MessageField.VALUE)
data = {"userId": "abc123", "country": "FR"}
payload = serializer(data, ctx)

result = deserializer(payload, ctx)
assert result == data
```

## Custom object transformation (`from_dict`)

Pass a `from_dict` callable to convert the decoded dict into a domain object:

```python
from dataclasses import dataclass

@dataclass
class UserEvent:
    userId: str
    country: str

def from_dict(d: dict, ctx: SerializationContext) -> UserEvent:
    return UserEvent(userId=d["userId"], country=d["country"])

deserializer = AvroDeserializer(client, from_dict=from_dict)
event = deserializer(payload, ctx)
# event is a UserEvent instance, not a plain dict
```

When `from_dict` is `None` (the default), the decoded dict is returned directly.

## Schema caching

Schemas resolved during deserialization are cached after the first registry lookup. Repeated deserialization of messages sharing the same schema identifier results in exactly one registry HTTP call. The cache is thread-safe and shared across all deserializers using the same `ApicurioRegistryClient` instance.

## Error handling

```python
from apicurio_serdes._errors import (
    DeserializationError,
    RegistryConnectionError,
    SchemaNotFoundError,
)

try:
    result = deserializer(payload, ctx)
except DeserializationError as e:
    # Bad magic byte, too few bytes, Avro decode failure, or from_dict failure
    print(f"Deserialization failed: {e}")
    if e.__cause__:
        print(f"Caused by: {e.__cause__}")
except SchemaNotFoundError as e:
    # Schema ID from wire format not found in registry
    print(f"Unknown schema: {e.id_type}={e.id_value}")
except RegistryConnectionError as e:
    # Registry unreachable during schema resolution
    print(f"Registry at {e.url} is unreachable: {e}")
```

### Exception reference

| Exception | When |
|-----------|------|
| `DeserializationError` | Input fewer than 5 bytes, magic byte ≠ `0x00`, Avro payload undecodable, or `from_dict` raised |
| `SchemaNotFoundError` | Schema identifier from wire format not found in registry (HTTP 404) |
| `RegistryConnectionError` | Registry unreachable during schema resolution |
