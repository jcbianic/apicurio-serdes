# Research: Avro Deserializer (Consumer Side)

**Feature**: 002-avro-deserializer | **Date**: 2026-03-06

## Decision Log

Decisions D1-D7 were established in feature 001-avro-serializer and carry forward unchanged. This feature adds D8-D12 for deserializer-specific concerns.

### D8: ID-Based Schema Lookup Endpoints

**Decision**: Use `GET /ids/globalIds/{globalId}` and `GET /ids/contentIds/{contentId}` for reverse schema resolution.

**Rationale**:
- The serializer embeds a 4-byte numeric ID (globalId or contentId) in the wire format header
- The deserializer must reverse-map this ID to the schema content
- Apicurio Registry v3 provides dedicated ID-based endpoints for exactly this purpose
- Both endpoints return the raw schema content as `application/octet-stream`

**Endpoint details**:

| Endpoint | Path | Parameter | Response |
|----------|------|-----------|----------|
| By globalId | `GET /ids/globalIds/{globalId}` | int64 path param | Raw schema bytes |
| By contentId | `GET /ids/contentIds/{contentId}` | int64 path param | Raw schema bytes |

**Response format**:
- Body: raw binary content (for Avro schemas, this is the JSON schema text)
- Content-Type: `application/octet-stream`
- No `X-Registry-GlobalId` or `X-Registry-ContentId` response headers (unlike the artifact content endpoint used by the serializer)
- HTTP 404 when the ID does not exist

**Parsing**: Since the body is raw bytes containing the JSON schema text, use `json.loads(response.content)` to parse the schema dict. Do not use `response.json()` since the Content-Type is not `application/json`.

**Sources**: Apicurio Registry v3 OpenAPI spec, `IdsResourceImpl.java` source code.

### D9: fastavro Deserialization — schemaless_reader

**Decision**: Use `fastavro.schemaless_reader` for single-record Avro decoding.

**Rationale**:
- The serializer uses `fastavro.schemaless_writer` for encoding — `schemaless_reader` is its exact inverse
- Reads exactly one record from a binary stream (no Avro container file overhead)
- Supports pre-parsed schemas from `fastavro.parse_schema()` for optimal performance

**Function signature**:
```python
fastavro.schemaless_reader(
    fo: IO,                          # Binary file-like object
    writer_schema: str | list | dict, # Parsed schema
    reader_schema: str | list | dict | None = None,
) -> dict | str | float | int | bool | bytes | list | None
```

**Usage pattern**:
```python
import io
import fastavro

parsed_schema = fastavro.parse_schema(schema_dict)
record = fastavro.schemaless_reader(io.BytesIO(avro_payload), parsed_schema)
```

**Key behaviors**:
- `fo` must be a file-like object opened in binary mode — use `io.BytesIO(payload[5:])` to skip the 5-byte wire format header
- Returns a Python dict for record types
- `parse_schema()` should be called once per schema and cached — resolves named types and handles schema references
- On corrupt/incompatible data: raises `EOFError`, `StopIteration`, or other exceptions depending on the nature of the corruption

**Alternatives rejected**:
- `fastavro.reader` (container reader): Designed for Avro container files with embedded schema. Not applicable — wire format uses schemaless encoding.
- Manual struct unpacking: Fragile, error-prone, doesn't handle Avro type encoding rules (variable-length integers, union indexes, etc.).

### D10: Error Class Design — DeserializationError

**Decision**: Add `DeserializationError` to `_errors.py`. Extend `SchemaNotFoundError` with a `from_id` classmethod for ID-based lookup failures.

**Rationale**:
- `DeserializationError` mirrors `SerializationError` and covers: bad magic byte (FR-003), too few bytes (FR-004), from_dict hook failure (FR-009), Avro decode failure (FR-011)
- `SchemaNotFoundError` currently only accepts `(group_id, artifact_id)`. ID-based lookups need a different message format. A `from_id(id_type, id_value)` classmethod keeps the existing constructor stable while supporting the new use case.

**DeserializationError design**:
```python
class DeserializationError(Exception):
    def __init__(self, message: str, cause: Exception | None = None) -> None:
        super().__init__(message)
        if cause is not None:
            self.__cause__ = cause
```

- `message` parameter (not `cause`-only like `SerializationError`) because several FR cases are format validation errors with no underlying exception
- Optional `cause` for wrapping (FR-009 from_dict failure, FR-011 Avro decode failure)

**SchemaNotFoundError.from_id design**:
```python
@classmethod
def from_id(cls, id_type: str, id_value: int) -> SchemaNotFoundError:
    ...
```

- Preserves backward compatibility — existing `SchemaNotFoundError(group_id, artifact_id)` calls unchanged
- Sets `id_type` and `id_value` attributes on the instance for programmatic access
- Message format: `"Schema not found: {id_type} {id_value}"`

### D11: use_id Default Value — contentId for Deserializer

**Decision**: Default `use_id="contentId"` for `AvroDeserializer`, as specified in FR-006.

**Context**:
- The serializer (001) defaults to `use_id="globalId"` (per D6, matching Apicurio 3.x Java serde defaults)
- The deserializer spec (FR-006) specifies `use_id="contentId"` as the default
- These defaults are **intentionally different** — the spec explicitly states: "The value must match the `use_id` setting used by the producer's `AvroSerializer`"

**Rationale for the spec's choice**:
- `contentId` is content-addressed: the same schema content always maps to the same contentId, regardless of which artifact or version registered it
- `globalId` is version-specific: it changes with each new version registration
- For deserialization, content identity is what matters — two different globalIds can represent identical schema content
- Apicurio's Java serde documentation recommends `contentId` for new deployments

**User impact**: Users must explicitly configure `use_id` to match on serializer and deserializer. The quickstart documentation must make this clear.

### D12: ID-Based Schema Caching Strategy

**Decision**: Add a separate `_id_cache: dict[tuple[str, int], dict[str, Any]]` to `ApicurioRegistryClient` for ID-based lookups. Share the existing `_lock` for thread safety.

**Rationale**:
- The existing `_schema_cache` maps `(group_id, artifact_id)` to `CachedSchema` (schema + global_id + content_id)
- ID-based lookups return only the raw schema content (no global_id/content_id headers), so the value type differs
- A separate cache keeps types clean: `_schema_cache` for artifact-based lookups, `_id_cache` for ID-based lookups
- The same `_lock` (RLock) protects both caches — no additional synchronization needed
- Cache key format: `("globalId", 42)` or `("contentId", 7)`
- Same double-checked locking pattern as `get_schema` (NFR-001)

**Alternatives rejected**:
- Single mixed-type cache: Possible but muddies the type annotations and makes the cache harder to reason about.
- Deserializer-level cache: Moves caching responsibility out of the client, breaking the pattern established by the serializer where all registry caching lives in the client.

**Cache for parsed schemas**: The `AvroDeserializer` will maintain a separate `_parsed_cache: dict[int, Any]` mapping schema IDs to `fastavro.parse_schema()` results. This avoids re-parsing the same schema on every deserialization call. The client returns raw schema dicts; the deserializer handles fastavro-specific parsing.

## fastavro Deserialization Patterns

### Schemaless Reading (single record from bytes)

```python
import io
import json
import fastavro

# Parse schema from dict (fetched from registry)
schema_dict = json.loads(raw_schema_bytes)
parsed = fastavro.parse_schema(schema_dict)

# Read single record from Avro binary
record = fastavro.schemaless_reader(io.BytesIO(avro_payload), parsed)
```

### Error Handling

- Corrupt/truncated payload: raises `EOFError` or `StopIteration`
- Schema mismatch: raises `EOFError`, `TypeError`, or `ValueError` depending on the nature of the mismatch
- All decoding errors should be caught broadly (`except Exception`) and wrapped in `DeserializationError`

### Best Practices

- Always use `fastavro.parse_schema()` to normalize the schema before decoding — same as serialization
- Cache parsed schemas by schema ID to avoid repeated parsing
- Construct `io.BytesIO` from the payload slice (after wire format header) for clean stream positioning
