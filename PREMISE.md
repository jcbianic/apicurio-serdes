# apicurio-serdes Premise

## What

`apicurio-serdes` is a general-purpose, production-ready Python serialization/deserialization library for Apicurio Registry. It provides `AvroSerializer` and `AvroDeserializer` backed by the native Apicurio Registry v3 API, with an interface intentionally compatible with `confluent-kafka`'s schema registry API. The library supports both sync and async usage, configurable wire formats, schema caching, and treats `group_id` as a first-class citizen.

## Who

Python data engineers and backend developers who:
- Run Apicurio Registry on-prem, on OpenShift, or via Red Hat AMQ Streams.
- Produce or consume Kafka messages serialized with Avro.
- Are already familiar with `confluent-kafka` and its schema registry API and want minimal friction switching to native Apicurio integration.

## Why

No general-purpose, production-ready Python serde library for Apicurio Registry exists. The official guidance — pointing `confluent-kafka`'s `SchemaRegistryClient` at Apicurio's ccompat endpoint — breaks in real-world scenarios: it cannot send the `X-Registry-GroupId` header required for non-default schema groups, and the ccompat layer does not resolve cross-artifact schema references. The only native-API Python library (`avrocurio`) is Avro-only, async-only, tightly coupled to `dataclasses-avroschema`, and has no community adoption. `apicurio-serdes` fills this gap with a clean, typed, fully-tested PyPI package.

## Domain

Apache Kafka event streaming ecosystem with Avro schema serialization. Apicurio Registry is a production-grade schema registry used in Red Hat / OpenShift environments, exposing a native v3 REST API as well as a Confluent-compatible (ccompat) compatibility layer. Key terms:
- **Schema Registry**: A service that stores and versions Avro (and other format) schemas referenced by Kafka producers and consumers.
- **group_id / artifact_id**: Apicurio's two-level schema addressing model (group > artifact > version).
- **contentId / globalId**: Apicurio's schema identifiers embedded in the Kafka message wire format.
- **Confluent wire format**: A binary framing convention (`0x00` magic byte + 4-byte schema ID + payload) used by confluent-kafka and supported by Apicurio.
- **SerializationContext**: A thin object carrying the Kafka topic name and field (KEY or VALUE) at serialization time.

## Scope

**In scope (MVP):**
- `ApicurioRegistryClient` — HTTP client for the native Apicurio v3 API, handling `group_id`, `artifact_id`, version lookup, and schema caching.
- `AvroSerializer` — serializes a Python dict to Avro bytes with Confluent wire framing.
- `AvroDeserializer` — deserializes Avro bytes to a Python dict, resolving schema from the `contentId` embedded in the wire format.
- `SerializationContext` — thin dataclass carrying topic + field, compatible with confluent-kafka's interface.
- Wire format configuration: `WireFormat.CONFLUENT_PAYLOAD` (default) and `WireFormat.KAFKA_HEADERS`.
- Sync-first API with async variant.

**Out of scope (MVP):**
- Protobuf and JSON Schema support (architecture anticipates them; implementation deferred).
- Code generation from Avro schemas.
- Schema auto-registration.
- Apicurio v2 API support.
- aiokafka / kafka-python compatibility.
- Registry management (creating/deleting artifacts) — use `apicurioregistrysdk` for that.
