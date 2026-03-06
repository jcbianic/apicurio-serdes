# Quickstart: Avro Serializer (Producer Side)

**Feature**: 001-avro-serializer | **Date**: 2026-03-06

## Installation

```bash
pip install apicurio-serdes
```

## Basic Usage — Serialize a dict to Confluent-framed Avro bytes

```python
from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroSerializer
from apicurio_serdes.serialization import SerializationContext, MessageField

# 1. Create a registry client
client = ApicurioRegistryClient(
    url="http://localhost:8080/apis/registry/v3",
    group_id="com.example.schemas",
)

# 2. Create a serializer for a specific schema artifact
serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
)

# 3. Serialize a dict
ctx = SerializationContext(topic="user-events", field=MessageField.VALUE)
payload: bytes = serializer({"userId": "abc-123", "country": "FR"}, ctx)

# payload is now Confluent wire format:
#   0x00 + 4-byte globalId (default) + Avro binary
```

## With a Custom to_dict Hook

```python
from dataclasses import dataclass, asdict

@dataclass
class UserEvent:
    userId: str
    country: str

serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    to_dict=lambda obj, ctx: asdict(obj),
)

event = UserEvent(userId="abc-123", country="FR")
payload = serializer(event, ctx)
```

## Error Handling

```python
from apicurio_serdes._errors import SchemaNotFoundError, RegistryConnectionError, SerializationError

try:
    payload = serializer(data, ctx)
except SchemaNotFoundError as e:
    print(f"Schema not found: group={e.group_id}, artifact={e.artifact_id}")
except RegistryConnectionError as e:
    print(f"Registry unreachable: {e.url}")
except SerializationError as e:
    print(f"to_dict hook failed: {e.cause}")
except ValueError as e:
    print(f"Data does not match schema: {e}")
```

## Test Scenarios

### Scenario 1: End-to-end serialization (US1-SC1)

```python
def test_serialize_valid_dict():
    """Serialize a valid dict and verify Confluent wire format."""
    client = ApicurioRegistryClient(url=REGISTRY_URL, group_id="test-group")
    serializer = AvroSerializer(registry_client=client, artifact_id="TestRecord")
    ctx = SerializationContext(topic="test-topic", field=MessageField.VALUE)

    result = serializer({"name": "Alice", "age": 30}, ctx)

    assert result[0:1] == b'\x00'           # magic byte
    assert len(result[1:5]) == 4             # 4-byte content_id
    assert len(result) > 5                   # has Avro payload
```

### Scenario 2: Schema caching (US2-SC1)

```python
def test_schema_cached_after_first_call():
    """Second serialization must not trigger another HTTP call."""
    # Use httpx mock to count requests
    serializer(data1, ctx)
    serializer(data2, ctx)
    assert registry_call_count == 1
```

### Scenario 3: Custom to_dict hook (US3-SC1)

```python
def test_to_dict_hook_applied():
    """to_dict transforms input before Avro encoding."""
    serializer = AvroSerializer(
        registry_client=client,
        artifact_id="TestRecord",
        to_dict=lambda obj, ctx: {"name": obj.name, "age": obj.age},
    )
    result = serializer(some_object, ctx)
    # result should be valid Confluent-framed Avro bytes
```

### Scenario 4: Missing artifact raises error (Edge case)

```python
def test_missing_artifact_raises_error():
    """Non-existent artifact_id raises SchemaNotFoundError."""
    serializer = AvroSerializer(
        registry_client=client, artifact_id="NonExistent"
    )
    with pytest.raises(SchemaNotFoundError) as exc_info:
        serializer(data, ctx)
    assert "NonExistent" in str(exc_info.value)
```

### Scenario 5: Invalid data raises error (US1-SC3)

```python
def test_invalid_data_raises_error():
    """Dict missing required field raises ValueError."""
    serializer = AvroSerializer(
        registry_client=client, artifact_id="TestRecord"
    )
    with pytest.raises(ValueError):
        serializer({"name": "Alice"}, ctx)  # missing "age"
```
