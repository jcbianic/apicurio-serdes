# apicurio-serdes

**Python serialization library for Apicurio Registry, using the native v3 API.**

## The Problem

You use [Apicurio Registry](https://www.apicur.io/registry/) to manage your Avro schemas. Your Kafka producers are written in Python. The standard guidance is to point `confluent-kafka`'s `SchemaRegistryClient` at the Apicurio compatibility endpoint — but in practice this breaks:

- **Non-default groups are invisible.** `SchemaRegistryClient` cannot send the `X-Registry-GroupId` header that Apicurio requires for schemas stored outside the `default` group.
- **Cross-artifact schema references fail.** The compatibility layer does not resolve `$ref` pointers between Apicurio artifacts.

If your schemas live in a custom group — and in any non-trivial Apicurio deployment, they do — you are stuck.

## The Solution

`apicurio-serdes` talks directly to the Apicurio v3 API, bypassing the compatibility layer entirely. The API matches `confluent-kafka`'s calling conventions:

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

That's it. `group_id` is a first-class parameter. Schema references resolve against the registry natively, and the output is byte-compatible with any Confluent-format consumer.

## Who Is This For?

Python data engineers and backend developers who:

- Use **Apicurio Registry 3.x** (standalone or via Red Hat Service Registry)
- Produce Kafka messages serialized with **Avro**
- Need schemas organized in **non-default groups**
- Want a **familiar API** — if you have used `confluent-kafka`'s serializers, you already know this library

## Key Features

| Feature | Description |
|---------|-------------|
| **Native v3 API** | Direct calls to Apicurio REST API, no ccompat workarounds |
| **`group_id` as first-class citizen** | Every schema lookup routes through the correct group |
| **confluent-kafka-compatible API** | Same class names and calling conventions as `confluent-kafka` |
| **Schema caching** | One HTTP call per artifact, not per message |
| **Wire format choice** | `globalId` (default) or `contentId` in the Confluent header |
| **Custom `to_dict` hooks** | Serialize dataclasses, Pydantic models, or any object |

## Get Started

Follow the [Quickstart](getting-started/quickstart.md) to serialize your first message in five minutes.

Already using `confluent-kafka`? Read the [Migration Guide](migration/from-confluent-kafka.md).

## Status

| Component | Status |
|-----------|--------|
| `ApicurioRegistryClient` | Available |
| `AvroSerializer` | Available |
| `AvroDeserializer` | Available |
| Async registry client | Available |
| Kafka headers wire format | Available |
| Protobuf support | Roadmap |
| JSON Schema support | Roadmap |
