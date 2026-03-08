# Wire Format

`apicurio-serdes` produces bytes in the **Confluent wire format** — the same framing used by `confluent-kafka`'s serializers. This page explains what each byte means and why.

## Byte Layout

Every serialized message has three parts:

```text
┌────────┬──────────────────────────┬────────────────────────┐
│ Byte 0 │       Bytes 1–4          │       Bytes 5+         │
│  0x00  │  Schema ID (big-endian)  │  Avro binary payload   │
│ magic  │     4-byte uint32        │  (schemaless encoding) │
└────────┴──────────────────────────┴────────────────────────┘
```

### Magic Byte (`0x00`)

The first byte is always `0x00`. It signals to consumers that this message uses the Confluent wire format (as opposed to raw Avro or another framing convention). Consumers check this byte before attempting to decode the rest of the message.

### Schema Identifier (Bytes 1–4)

A 4-byte big-endian unsigned integer that identifies which schema was used to encode the Avro payload. Consumers use this ID to fetch the correct schema from the registry before decoding.

The ID can be one of two types, depending on configuration:

| Identifier | What it represents | When to use |
|------------|--------------------|-------------|
| **globalId** | A unique, auto-incremented ID assigned to each artifact version when it is created. Globally unique across the entire registry. | Default. Use this unless you have a specific reason not to. |
| **contentId** | A content-addressed ID derived from the schema bytes. Two identical schemas always share the same `contentId`, even if they are registered as different artifacts. | Use when consumers resolve schemas by content hash rather than by version history. |

In `apicurio-serdes`, you choose the identifier with the `use_id` parameter:

```python
# Default: embed the globalId
serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    use_id="globalId",
)

# Alternative: embed the contentId
serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    use_id="contentId",
)
```

### Avro Binary Payload (Bytes 5+)

The remaining bytes are the Avro binary encoding of the data, written using **schemaless encoding** (fastavro's `schemaless_writer`). The schema is not embedded in the payload — it is resolved from the registry using the schema ID in bytes 1–4.

## Why This Format Exists

The Confluent wire format solves a fundamental problem in event streaming: **producers and consumers must agree on the schema, but you don't want to send the schema with every message.**

By embedding a compact schema ID in the message header, the consumer can:

1. Read the 4-byte ID from the header
2. Fetch the schema from the registry (typically cached after the first fetch)
3. Decode the Avro payload using that schema

This keeps messages small while preserving full schema awareness.

## Compatibility

Messages produced by `apicurio-serdes` are byte-compatible with messages produced by `confluent-kafka`'s `AvroSerializer`. Any consumer that understands the Confluent wire format can decode them, provided it can resolve the schema ID from the same registry.

The only requirement is that producer and consumer agree on which ID type is in the header (`globalId` vs `contentId`). If the producer embeds a `contentId` but the consumer expects a `globalId`, the lookup will return the wrong schema or fail.
