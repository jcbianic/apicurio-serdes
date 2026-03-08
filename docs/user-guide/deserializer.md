# Avro Deserializer

`AvroDeserializer` reads Confluent wire-format bytes, resolves the embedded
schema identifier against the Apicurio Registry, and returns a Python dict
(or a domain object when a `from_dict` hook is configured).

## Installation

```bash
pip install apicurio-serdes
```

## Basic usage

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
record = deserializer(kafka_message_bytes, ctx)
# record is a Python dict: {"userId": "abc123", "country": "FR"}
```

## Round-trip with AvroSerializer

The `use_id` parameter must match on serializer and deserializer.

```python
from apicurio_serdes.avro import AvroSerializer, AvroDeserializer

serializer = AvroSerializer(client, "UserEvent", use_id="contentId")
deserializer = AvroDeserializer(client, use_id="contentId")

ctx = SerializationContext("events", MessageField.VALUE)
data = {"userId": "abc123", "country": "FR"}
payload = serializer(data, ctx)

result = deserializer(payload, ctx)
assert result == data  # round-trip fidelity (SC-002, SC-005)
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

## Schema identifier mode (`use_id`)

The Confluent wire format stores a 4-byte schema identifier in bytes 1–4.
The `use_id` parameter controls how that integer is interpreted:

| `use_id`     | Registry endpoint           | Default |
|--------------|-----------------------------|---------|
| `"contentId"` | `GET /ids/contentIds/{id}` | ✓       |
| `"globalId"` | `GET /ids/globalIds/{id}`  |         |

```python
# contentId (default — matches Apicurio's native wire format)
deserializer = AvroDeserializer(client)

# globalId (use when producer embedded a globalId)
deserializer = AvroDeserializer(client, use_id="globalId")
```

## Schema caching

Resolved schemas are cached after the first registry lookup. Processing
1 000 messages with the same schema ID costs exactly 1 HTTP call (SC-003).
The cache is thread-safe (NFR-001).

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
    print(f"Unknown schema: {e}")
except RegistryConnectionError as e:
    # Registry unreachable
    print(f"Registry at {e.url} is down: {e}")
```

### Error reference

| Situation | Exception | Condition |
|-----------|-----------|-----------|
| Input fewer than 5 bytes | `DeserializationError` | FR-004 |
| Magic byte ≠ `0x00` | `DeserializationError` | FR-003 |
| Schema ID not in registry | `SchemaNotFoundError` | FR-010 |
| Registry unreachable | `RegistryConnectionError` | FR-012 |
| Avro payload undecodable | `DeserializationError` | FR-011 |
| `from_dict` raises | `DeserializationError` | FR-009 |
