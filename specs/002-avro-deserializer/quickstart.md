# Quickstart: Avro Deserializer (Consumer Side)

**Feature**: 002-avro-deserializer | **Date**: 2026-03-06

## Basic Deserialization

```python
from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroDeserializer
from apicurio_serdes.serialization import SerializationContext, MessageField

# 1. Create a registry client
client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="my-group",
)

# 2. Create a deserializer
deserializer = AvroDeserializer(client, use_id="globalId")

# 3. Deserialize Kafka message bytes
ctx = SerializationContext("my-topic", MessageField.VALUE)
record = deserializer(kafka_message_bytes, ctx)
# record is a Python dict: {"userId": "abc123", "country": "FR"}
```

## Round-Trip (Serialize + Deserialize)

```python
from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroSerializer, AvroDeserializer
from apicurio_serdes.serialization import SerializationContext, MessageField

client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="my-group",
)

# Serialize
serializer = AvroSerializer(client, "UserEvent", use_id="globalId")
ctx = SerializationContext("events", MessageField.VALUE)
data = {"userId": "abc123", "country": "FR"}
payload = serializer(data, ctx)

# Deserialize (use_id must match the serializer)
deserializer = AvroDeserializer(client, use_id="globalId")
result = deserializer(payload, ctx)

assert result == data  # Round-trip fidelity (SC-002)
```

**Important**: The `use_id` parameter must match on both serializer and deserializer. If the serializer embeds a `globalId`, the deserializer must interpret it as a `globalId`.

## Custom Object Transformation (from_dict)

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
    print(f"Registry at {e.url} is down: {e}")
```

## Test Scenarios

### Scenario 1: Valid Confluent-framed Avro bytes decode to dict

```python
# Given: a configured client and deserializer
# When: called with valid Confluent-framed bytes
result = deserializer(valid_confluent_bytes, ctx)
# Then: returns a dict matching the original data
assert result == {"userId": "abc123", "country": "FR"}
```

### Scenario 2: Schema caching prevents redundant lookups

```python
# Given: a deserializer
# When: two messages with the same schema ID are deserialized
result1 = deserializer(message1_bytes, ctx)
result2 = deserializer(message2_bytes, ctx)
# Then: the registry was contacted exactly once for that schema ID
```

### Scenario 3: Invalid magic byte raises DeserializationError

```python
import pytest
bad_bytes = b"\x01" + b"\x00\x00\x00\x2a" + b"..."
with pytest.raises(DeserializationError, match="magic byte"):
    deserializer(bad_bytes, ctx)
```

### Scenario 4: Round-trip fidelity

```python
original = {"userId": "abc123", "country": "FR"}
payload = serializer(original, ctx)
decoded = deserializer(payload, ctx)
assert decoded == original
```
