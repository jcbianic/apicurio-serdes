# apicurio-serdes

Python serialization/deserialization library for [Apicurio Registry](https://www.apicur.io/registry/) using the native v3 API.

## Why apicurio-serdes?

The standard guidance for Python Kafka producers using Apicurio Registry is to point `confluent-kafka`'s `SchemaRegistryClient` at the ccompat endpoint. In practice this breaks:

- Schemas in **non-default groups** require an `X-Registry-GroupId` HTTP header that `SchemaRegistryClient` cannot send.
- **Cross-artifact schema references** are not resolved by the ccompat layer.

`apicurio-serdes` solves this by talking directly to the Apicurio v3 API, with an interface modelled after `confluent-kafka` so the learning curve is minimal.

## Key Features

- **Native Apicurio v3 API** — no ccompat workarounds
- **`group_id` as a first-class citizen** — every lookup routes through the correct group
- **confluent-kafka-compatible API** — familiar class names and method signatures
- **Schema caching** — one HTTP call per artifact, not per message
- **Sync-first** with async variant planned
- **Wire format choice** — Confluent payload framing (default) or Kafka headers

## Quick Example

```python
from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroSerializer
from apicurio_serdes.serialization import SerializationContext, MessageField

client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="com.example.schemas",
)

serializer = AvroSerializer(registry_client=client, artifact_id="UserEvent")
ctx = SerializationContext(topic="user-events", field=MessageField.VALUE)

payload: bytes = serializer({"userId": "abc", "country": "FR"}, ctx)
```

## Status

| Component | Status |
|---|---|
| `ApicurioRegistryClient` | Available |
| `AvroSerializer` | Available |
| `AvroDeserializer` | In progress |
| Async registry client | Planned |
| Kafka headers wire format | Planned |
| Protobuf support | Roadmap |
| JSON Schema support | Roadmap |
