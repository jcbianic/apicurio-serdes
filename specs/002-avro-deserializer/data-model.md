# Data Model: Avro Deserializer (Consumer Side)

**Feature**: 002-avro-deserializer | **Date**: 2026-03-06

## New Entities

### AvroDeserializer

Deserializer for Confluent-framed Avro bytes. Callable as `deserializer(data, ctx)`.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `registry_client` | `ApicurioRegistryClient` | Yes | -- | Registry client for schema resolution |
| `from_dict` | `Callable[[dict, SerializationContext], Any] \| None` | No | `None` | Optional post-decode transformation (FR-008) |
| `use_id` | `Literal["globalId", "contentId"]` | No | `"contentId"` | Which ID type the wire format field represents (FR-006) |
| `_parsed_cache` | `dict[int, Any]` | Internal | `{}` | Maps schema ID to `fastavro.parse_schema()` result |

**Methods**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `__call__` | `(data: bytes, ctx: SerializationContext) -> Any` | Deserializes Confluent-framed Avro bytes to a Python dict or domain object (FR-002) |

**Call flow**:
1. Validate input length >= 5 bytes (FR-004)
2. Validate magic byte == `0x00` (FR-003)
3. Extract 4-byte schema ID: `struct.unpack(">I", data[1:5])[0]`
4. Resolve schema from registry by ID (FR-005), using `use_id` to select the endpoint
5. Parse schema with `fastavro.parse_schema()` if not already cached
6. Decode Avro payload: `fastavro.schemaless_reader(BytesIO(data[5:]), parsed_schema)`
7. If `from_dict` is provided, apply it: `result = from_dict(decoded_dict, ctx)` (FR-008)
8. Return result

---

### DeserializationError

Error raised for deserialization failures.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | `str` | Yes | Descriptive error message |
| `__cause__` | `Exception \| None` | No | Original exception when wrapping (FR-009, FR-011) |

**Raised by**:
- FR-003: Invalid magic byte
- FR-004: Input too short (< 5 bytes)
- FR-009: `from_dict` callable failure
- FR-011: Avro decoding failure

---

## Modified Entities

### ApicurioRegistryClient (extended)

Two new methods for ID-based schema resolution, plus a new internal cache.

**New fields**:

| Field | Type | Description |
|-------|------|-------------|
| `_id_cache` | `dict[tuple[str, int], dict[str, Any]]` | Maps `(id_type, id_value)` to parsed schema dict |

**New methods**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_schema_by_global_id` | `(global_id: int) -> dict[str, Any]` | Retrieves schema by globalId from `/ids/globalIds/{globalId}`. Caches result. |
| `get_schema_by_content_id` | `(content_id: int) -> dict[str, Any]` | Retrieves schema by contentId from `/ids/contentIds/{contentId}`. Caches result. |

Both methods use the same `_lock` as `get_schema` for thread safety (NFR-001).

### SchemaNotFoundError (extended)

New classmethod for ID-based lookup failures.

**New classmethod**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `from_id` | `(cls, id_type: str, id_value: int) -> SchemaNotFoundError` | Creates error for ID-based lookup 404s (FR-010) |

**New attributes** (on instances created via `from_id`):

| Attribute | Type | Description |
|-----------|------|-------------|
| `id_type` | `str` | `"globalId"` or `"contentId"` |
| `id_value` | `int` | The numeric ID that was not found |

---

## Relationships

```
AvroSerializer ──┐                          ┌── get_schema(artifact_id)
                 ├──→ ApicurioRegistryClient ├── get_schema_by_global_id(id)
AvroDeserializer ┘          │               └── get_schema_by_content_id(id)
      │                     │
      │                     ├── _schema_cache (artifact-based, for serializer)
      │                     ├── _id_cache (ID-based, for deserializer)
      │                     └── _lock (shared RLock)
      │                     │
      ├── receives → SerializationContext
      │                  └── contains → MessageField
      │
      ├── optionally applies → from_dict callable
      │
      └── maintains → _parsed_cache (fastavro parsed schemas)
```

## Validation Rules

| Entity | Rule | Source |
|--------|------|--------|
| `AvroDeserializer` input bytes | Must be >= 5 bytes | FR-004 |
| `AvroDeserializer` magic byte | Must be `0x00` | FR-003 |
| Schema ID from wire format | Must resolve to a schema in the registry | FR-005, FR-010 |
| Avro payload | Must be decodable with the resolved schema | FR-011 |
| `from_dict` callable | Must not raise; if it does, error is wrapped | FR-009 |

## State Transitions

### ID-Based Schema Cache (per schema ID)

```
[Empty] ──first lookup──→ [Fetching] ──HTTP 200──→ [Cached]
                               │
                               ├──HTTP 404──→ SchemaNotFoundError.from_id(...)
                               └──network error──→ RegistryConnectionError
```

### Deserialization Flow

```
[Raw bytes] ──validate──→ [Framed] ──extract ID──→ [Schema resolved]
                │                        │                 │
                ├──< 5 bytes─→ DeserializationError        │
                └──bad magic─→ DeserializationError        │
                                         │                 │
                                  [Schema not found]───→ SchemaNotFoundError
                                                           │
                                                    [Decode] ──success──→ [Dict]
                                                       │                    │
                                                       │            [from_dict applied]
                                                       │                    │
                                                decode fail──→ DeserializationError
                                                        from_dict fail──→ DeserializationError
```

Once cached, a schema remains cached for the lifetime of the client. No eviction or TTL in MVP scope.
