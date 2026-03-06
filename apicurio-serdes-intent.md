# apicurio-serdes — Project Intent

## Problem Statement

Apicurio Registry is a production-grade schema registry used widely in Red Hat / OpenShift environments. Its Java serde modules are excellent. Python support does not exist at the same level.

The official guidance for Python producers and consumers is: point your `confluent-kafka` `SchemaRegistryClient` at the Apicurio ccompat endpoint (`/apis/ccompat/v7`). This works for the simplest cases but breaks in practice when:

- Schemas are registered under a non-default **group** — the ccompat API requires an `X-Registry-GroupId` HTTP header that `SchemaRegistryClient` cannot send.
- Schemas use **cross-artifact references** — the ccompat layer does not resolve them.

The only Python library that uses the native Apicurio v3 API is `avrocurio` (castoredc), which is Avro-only, tightly coupled to `dataclasses-avroschema`, async-only, and has 0 community adoption.

**The gap:** no general-purpose, production-ready Python serde library for Apicurio Registry exists.

---

## Goals

- Provide `AvroSerializer` and `AvroDeserializer` backed by the **Apicurio Registry native v3 API**.
- Support the `group_id` / `artifact_id` model natively in the client.
- Expose an API **intentionally compatible** with `confluent-kafka`'s schema registry interface so that users familiar with that library have minimal friction.
- Support both **sync and async** usage patterns.
- Be **format-agnostic** in architecture from day one, even if Avro is the only supported format at MVP.
- Ship as a clean PyPI package: typed, documented, 100% test coverage.

---

## Non-Goals (MVP)

- Protobuf and JSON Schema support (architecture must anticipate them, implementation deferred).
- Code generation from Avro schemas (separate concern, separate tool).
- Schema auto-registration.
- Apicurio v2 API support.
- Compatibility with `aiokafka` or `kafka-python` (can be added later without API changes).

---

## Target Users

Python data engineers and backend developers who:

- Use Apicurio Registry (on-prem, OpenShift, or Red Hat AMQ Streams).
- Produce or consume Kafka messages serialized with Avro.
- Are already familiar with `confluent-kafka` and its schema registry API.

---

## Design Principles

**1. API compatibility with confluent-kafka**
Users should be able to read the confluent-kafka docs and apply the same mental model. Class names, method signatures, and configuration patterns should feel familiar.

**2. No opinion on schema representation**
The library works with plain dicts and raw Avro schema strings. It does not require `dataclasses-avroschema`, Pydantic, or any other schema definition library.

**3. group_id is a first-class citizen**
`ApicurioRegistryClient` accepts `group_id` as a top-level parameter. Every schema lookup routes through the correct group.

**4. Configurable wire format**
Default: Confluent-compatible framing (`0x00` + `contentId` as 4-byte big-endian int + Avro payload). Alternative: schema ID in Kafka message headers. The format is configured at the client level, not buried in internals.

**5. Schema caching**
The client caches resolved schemas by `(group_id, artifact_id)` after the first fetch. No repeated HTTP calls per message.

**6. Sync-first, async-friendly**
The primary interface is synchronous (matching confluent-kafka). An async variant is exposed without duplicating logic.

---

## Target API

```python
from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroSerializer, AvroDeserializer
from apicurio_serdes.serialization import SerializationContext, MessageField

# Client — owns the registry connection and schema cache
client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="com.example.schemas",
)

# Serializer — bound to one artifact
serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    to_dict=lambda obj, ctx: obj.model_dump(),   # optional, identity by default
)

# Deserializer — resolves artifact from wire format at runtime
deserializer = AvroDeserializer(
    registry_client=client,
    from_dict=lambda d, ctx: d,                  # optional, identity by default
)

# Usage in a producer
ctx = SerializationContext(topic="user-events", field=MessageField.VALUE)
payload: bytes = serializer({"userId": "abc", "country": "FR"}, ctx)

# Usage in a consumer
record: dict = deserializer(payload, ctx)
```

---

## MVP Scope

| Component | Description |
|---|---|
| `ApicurioRegistryClient` | HTTP client for native Apicurio v3 API. Handles group_id, artifact_id, version lookup, schema caching. |
| `AvroSerializer` | Serializes a dict to Avro bytes with Confluent wire framing. Fetches schema on first call. |
| `AvroDeserializer` | Deserializes Avro bytes to dict. Resolves schema from contentId embedded in wire format. |
| `SerializationContext` | Thin dataclass carrying topic + field (KEY or VALUE). Compatible with confluent-kafka's interface. |
| Wire format config | `WireFormat.CONFLUENT_PAYLOAD` (default) or `WireFormat.KAFKA_HEADERS`. |

---

## Differentiators vs Existing Solutions

| | `confluent-kafka` + ccompat | `avrocurio` | **`apicurio-serdes`** |
|---|---|---|---|
| Native Apicurio v3 API | No | Yes | Yes |
| group_id support | No | No | Yes |
| Avro | Yes | Yes | Yes |
| Protobuf | Yes | No | Planned |
| JSON Schema | Yes | No | Planned |
| confluent-kafka API compatibility | Native | No | Yes |
| Sync + async | Sync | Async only | Both |
| Schema library agnostic | Yes | No (dataclasses-avroschema) | Yes |
| Wire format choice | Limited | No | Yes |

---

## Open Questions

1. **Community validation** — Contact Apicurio maintainers before writing code to confirm there is no ongoing internal Python serde effort and to explore potential endorsement.

2. **contentId vs globalId** — Confluent wire format uses a single schema ID. Apicurio has both. The MVP defaults to `contentId` (Apicurio 3.x serde default), but this should be validated with the Apicurio team.

3. **Minimum Python version** — Python 3.10+ (union types, structural pattern matching) or 3.9+ for broader compatibility?

4. **fastavro vs apache-avro** — `fastavro` is faster and more Pythonic. `apache-avro` is the reference implementation. We default to `fastavro` but the choice deserves explicit justification in the docs.

---

## What This Is Not

This library is not a registry management client. For creating, reading, or deleting schema artifacts in Apicurio, use the official `apicurioregistrysdk` Python package.

This library is not a code generator. Generating Python classes from Avro schemas is a separate concern and a potential future companion tool.
