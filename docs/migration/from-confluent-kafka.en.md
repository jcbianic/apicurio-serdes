# Migrating from confluent-kafka

This guide maps every difference between `confluent-kafka`'s schema registry serializers and `apicurio-serdes`, so you can update your existing producer code with confidence.

## API Comparison

### Class Names

| confluent-kafka | apicurio-serdes | Notes |
|-----------------|-----------------|-------|
| `SchemaRegistryClient` | `ApicurioRegistryClient` | Different constructor parameters |
| `AvroSerializer` | `AvroSerializer` | Same name, same calling convention |
| `SerializationContext` | `SerializationContext` | Same interface |
| `MessageField` | `MessageField` | Same enum values (`KEY`, `VALUE`) |

### Constructor Parameters

=== "confluent-kafka"

    ```python
    from confluent_kafka.schema_registry import SchemaRegistryClient
    from confluent_kafka.schema_registry.avro import AvroSerializer

    registry = SchemaRegistryClient({
        "url": "http://registry:8080/apis/ccompat/v7",
    })
    serializer = AvroSerializer(
        schema_registry_client=registry,
        schema_str='{"type":"record","name":"UserEvent",...}',
        to_dict=my_to_dict,
    )
    ```

=== "apicurio-serdes"

    ```python
    from apicurio_serdes import ApicurioRegistryClient
    from apicurio_serdes.avro import AvroSerializer

    client = ApicurioRegistryClient(
        url="http://registry:8080/apis/registry/v3",
        group_id="com.example.schemas",
    )
    serializer = AvroSerializer(
        registry_client=client,
        artifact_id="UserEvent",
        to_dict=my_to_dict,
    )
    ```

Key differences:

| Parameter | confluent-kafka | apicurio-serdes |
|-----------|-----------------|-----------------|
| Registry URL | ccompat endpoint (`/apis/ccompat/v7`) | Native v3 endpoint (`/apis/registry/v3`) |
| Schema source | `schema_str` (inline Avro JSON) | `artifact_id` (fetched from registry) |
| Group | Not applicable | `group_id` (**required** on client) |
| Wire format ID | Not configurable (uses schema ID) | `use_id` — `"globalId"` (default) or `"contentId"` |
| Strict mode | Not available | `strict=True` rejects extra fields |

### Invocation Patterns

The serialization call itself is identical:

```python
# Both libraries use the same calling convention
ctx = SerializationContext(topic="user-events", field=MessageField.VALUE)
payload: bytes = serializer({"userId": "abc", "country": "FR"}, ctx)
```

### Exception Types

| confluent-kafka | apicurio-serdes | When |
|-----------------|-----------------|------|
| `SchemaRegistryError` | `SchemaNotFoundError` | Artifact does not exist (404) |
| `KafkaException` (network) | `RegistryConnectionError` | Registry unreachable |
| N/A | `SerializationError` | `to_dict` hook raised an exception |
| `SerializerError` | `ValueError` | Data does not match schema |

## Understanding `group_id`

`group_id` is the most important difference. Apicurio Registry organizes schemas in a three-level hierarchy (group → artifact → version), whereas Confluent Schema Registry uses a flat namespace with no group concept. See [Addressing Model](../concepts/addressing-model.md) for a full explanation.

When migrating, map your Confluent subjects to Apicurio groups and artifacts:

| Confluent subject | Apicurio group | Apicurio artifact |
|-------------------|----------------|-------------------|
| `user-events-value` | `com.example.schemas` | `UserEvent` |
| `order-events-key` | `com.example.schemas` | `OrderKey` |

A common convention for the group is your organisation's reverse-domain name (e.g., `com.example.schemas`).

## Behavioral Differences

| Behavior | confluent-kafka | apicurio-serdes |
|----------|-----------------|-----------------|
| Schema source | Inline JSON string or auto-registered | Always fetched from registry by `artifact_id` |
| Auto-registration | Supported (`auto.register.schemas=True`) | Not supported — schemas must exist in the registry |
| Schema caching | Per `SchemaRegistryClient` instance | Per `ApicurioRegistryClient` instance |
| Thread safety | Thread-safe | Thread-safe |
| Wire format | Confluent framing (`0x00` + 4-byte ID) | Same Confluent framing (compatible) |
| Schema evolution | Handled by registry compatibility rules | Same — Apicurio enforces compatibility rules |

## Minimal Migration Example

### Before (confluent-kafka)

```python
from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import (
    SerializationContext,
    MessageField,
)

schema_str = '{"type":"record","name":"UserEvent","fields":[{"name":"userId","type":"string"},{"name":"country","type":"string"}]}'

registry = SchemaRegistryClient({"url": "http://registry:8080/apis/ccompat/v7"})
serializer = AvroSerializer(registry, schema_str)

producer = Producer({"bootstrap.servers": "kafka:9092"})
ctx = SerializationContext("user-events", MessageField.VALUE)

producer.produce("user-events", value=serializer({"userId": "abc", "country": "FR"}, ctx))
producer.flush()
```

### After (apicurio-serdes)

```python
from confluent_kafka import Producer
from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroSerializer
from apicurio_serdes.serialization import SerializationContext, MessageField

client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="com.example.schemas",
)
serializer = AvroSerializer(registry_client=client, artifact_id="UserEvent")

producer = Producer({"bootstrap.servers": "kafka:9092"})
ctx = SerializationContext("user-events", MessageField.VALUE)

producer.produce("user-events", value=serializer({"userId": "abc", "country": "FR"}, ctx))
producer.flush()
```

The import lines and client configuration changed. The `producer.produce()` call is identical: the output bytes are the same Confluent wire format.

## Next Steps

- [Addressing Model](../concepts/addressing-model.md) — understand the group/artifact/version hierarchy
- [Quickstart](../getting-started/quickstart.md) — full working example from scratch
- [API Reference](../api-reference/index.md) — complete parameter documentation
