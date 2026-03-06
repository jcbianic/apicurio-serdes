# Data Model: Avro Serializer (Producer Side)

**Feature**: 001-avro-serializer | **Date**: 2026-03-06

## Entities

### ApicurioRegistryClient

Registry accessor. Owns the HTTP connection and schema cache.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | `str` | Yes | Base URL of the Apicurio Registry v3 API (e.g., `http://registry:8080/apis/registry/v3`) |
| `group_id` | `str` | Yes | Schema group identifier applied to every lookup (FR-009) |
| `_http_client` | `httpx.Client` | Internal | Persistent HTTP session for connection pooling |
| `_schema_cache` | `dict[tuple[str, str], CachedSchema]` | Internal | Maps `(group_id, artifact_id)` to cached schema + metadata |

**Methods**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_schema` | `(artifact_id: str) -> CachedSchema` | Retrieves schema from cache or registry. Returns cached on subsequent calls (FR-006). Raises `SchemaNotFoundError` if artifact does not exist (FR-008). |

**Lifecycle**: Created once per registry connection. Shared across multiple serializers. Cache lives for the lifetime of the client instance.

---

### CachedSchema

Internal value object holding a resolved schema and its registry metadata.

| Field | Type | Description |
|-------|------|-------------|
| `schema` | `dict` | Parsed Avro schema (JSON parsed to Python dict, then parsed by fastavro) |
| `content_id` | `int` | Apicurio `contentId` used in Confluent wire format header |

**Note**: This is an internal type, not part of the public API.

---

### AvroSerializer

Serializer bound to a single artifact. Callable as `serializer(data, ctx)`.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `registry_client` | `ApicurioRegistryClient` | Yes | — | Registry client for schema retrieval |
| `artifact_id` | `str` | Yes | — | Artifact identifier in the registry |
| `to_dict` | `Callable[[Any, SerializationContext], dict] \| None` | No | `None` | Optional transformation hook (FR-007) |
| `_schema` | `CachedSchema \| None` | Internal | `None` | Lazily fetched on first `__call__` |

**Methods**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `__call__` | `(data: Any, ctx: SerializationContext) -> bytes` | Serializes data to Confluent-framed Avro bytes (FR-005) |

**Call flow**:
1. If `to_dict` is provided, apply it: `data = self.to_dict(data, ctx)`
2. Fetch schema via `registry_client.get_schema(artifact_id)` (lazy, cached)
3. Encode `data` to Avro binary using `fastavro.schemaless_writer`
4. Prepend Confluent wire format header: `0x00` + `struct.pack(">I", content_id)`
5. Return concatenated bytes

---

### SerializationContext

Thin context object carrying Kafka metadata at serialization time.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `topic` | `str` | Yes | Target Kafka topic name |
| `field` | `MessageField` | Yes | Whether this datum is a message key or value |

---

### MessageField

Enumeration identifying the message field type.

| Value | Description |
|-------|-------------|
| `KEY` | Kafka message key |
| `VALUE` | Kafka message value |

---

## Relationships

```
AvroSerializer ──uses──→ ApicurioRegistryClient ──HTTP──→ Apicurio Registry v3
      │                          │
      │                          ├── owns → _schema_cache
      │                          │             └── CachedSchema (schema + content_id)
      │                          │
      ├── receives → SerializationContext
      │                  └── contains → MessageField
      │
      └── optionally applies → to_dict callable
```

## Validation Rules

| Entity | Rule | Source |
|--------|------|--------|
| `ApicurioRegistryClient.url` | Must be a valid URL string | FR-001 |
| `ApicurioRegistryClient.group_id` | Must be non-empty string | FR-009 |
| `AvroSerializer` input data | Must conform to the Avro schema (validated by fastavro) | FR-002, US1-SC3 |
| Wire format output | Must be `0x00` + 4-byte big-endian `content_id` + Avro binary | FR-003 |

## State Transitions

### Schema Cache (per artifact_id)

```
[Empty] ──first get_schema()──→ [Fetching] ──HTTP 200──→ [Cached]
                                     │
                                     └──HTTP 404──→ SchemaNotFoundError
                                     └──HTTP error──→ network exception
```

Once cached, a schema remains cached for the lifetime of the client. No eviction or TTL in MVP scope.
