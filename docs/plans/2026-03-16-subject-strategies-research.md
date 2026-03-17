# Research: Subject / Artifact Name Strategies (2026-03-16)

## Problem Statement

Expand the existing artifact name strategy system so users can auto-derive
artifact IDs from Kafka topic names and/or Avro schema record names, covering
the full set of strategies offered by the Apicurio Java reference implementation
and Confluent Schema Registry. Both `AvroSerializer` and `AvroDeserializer` are
in scope.

## Requirements

- Add record-name–based strategies: `RecordIdStrategy` and `TopicRecordIdStrategy`
- Strategies must satisfy the existing `ArtifactResolver` protocol
  (`Callable[[SerializationContext], str]`) to remain backward-compatible
- Deserializer support: since the schema ID is embedded in the wire format, the
  deserializer does not need strategies for schema lookup — no changes required
- Do not change the `SerializationContext` dataclass or `ArtifactResolver`
  type alias

## Findings

### Relevant Files

| File | Purpose | Key Lines |
| --- | --- | --- |
| `src/apicurio_serdes/avro/_strategies.py` | `ArtifactResolver` type alias + strategies | 1–73 |
| `src/apicurio_serdes/serialization.py` | `SerializationContext(topic, field)` | 1–46 |
| `src/apicurio_serdes/avro/_serializer.py` | Consumes resolver; lazy caching | 101–216 |
| `src/apicurio_serdes/avro/_deserializer.py` | Wire-format schema lookup; no strategy | — |
| `src/apicurio_serdes/avro/__init__.py` | Public re-exports for `avro` sub-package | 1–19 |
| `tests/test_strategies.py` | Strategy unit tests; TDD anchor | 1–45 |

### Existing Patterns

**`ArtifactResolver` type alias**

```python
ArtifactResolver = Callable[["SerializationContext"], str]
```

Any callable `(ctx: SerializationContext) -> str` satisfies the protocol. Both
built-in strategies are callable classes that implement `__call__`.

**`SerializationContext` shape**

```python
@dataclass(frozen=True)
class SerializationContext:
    topic: str
    field: MessageField   # MessageField.KEY or MessageField.VALUE
```

The context carries **no schema information**. Topic-based strategies are
trivial; record-name–based strategies must receive the schema via another
mechanism (see Recommendations).

**`TopicIdStrategy`** — `"{topic}-{field}"` (e.g. `"orders-value"`)

**`SimpleTopicIdStrategy`** — `"{topic}"` (e.g. `"orders"`)

**`AvroSerializer` lazy resolution** (`_serializer.py` lines 180–216):
The resolver is called exactly once on the first `serialize()` call and the
result is cached in `_resolved_artifact_id`. The strategy is called with the
live `SerializationContext` from that first call.

**Auto-registration pattern**: `AvroSerializer` already accepts `schema=` at
construction time for `auto_register=True`. This constructor injection pattern
is the right model for schema-aware strategies.

**Mutual exclusivity**: `artifact_id` and `artifact_resolver` are mutually
exclusive — exactly one must be provided.

### Dependencies

- No new external libraries needed
- `fastavro.parse_schema` is already available for schema introspection if needed
- Strategies must remain pure callables — no registry access, no I/O

### External Research

**Confluent naming conventions** (from Confluent Schema Registry documentation):

| Strategy | Formula | Key/value suffix? |
| --- | --- | --- |
| `TopicNameStrategy` | `{topic}-{key\|value}` | Yes |
| `RecordNameStrategy` | `{namespace}.{RecordName}` | No |
| `TopicRecordNameStrategy` | `{topic}-{namespace}.{RecordName}` | No |

Critical: the `-key`/`-value` suffix is **exclusive to `TopicNameStrategy`**.
`RecordNameStrategy` and `TopicRecordNameStrategy` use the fully-qualified record
name without any suffix.

**Apicurio Java strategies** (from Apicurio Registry Java SDK):

| Strategy | Artifact ID | GroupId |
| --- | --- | --- |
| `TopicIdStrategy` | `{topic}-{key\|value}` | configured |
| `SimpleTopicIdStrategy` | `{topic}` | configured |
| `RecordIdStrategy` | `{RecordName}` | `{namespace}` |
| `TopicRecordIdStrategy` | `{topic}-{namespace}.{RecordName}` | configured |
| `QualifiedRecordIdStrategy` | `{namespace}.{RecordName}` | configured |

Notes:

- `RecordIdStrategy` routes to a **different groupId** (namespace) — incompatible
  with the current single-group-per-client design
- `QualifiedRecordIdStrategy` is the most practical record-name strategy when
  keeping a single configured groupId
- `TopicRecordIdStrategy` prefixes the topic, same logic as Confluent's
  `TopicRecordNameStrategy`
- Apicurio's official Python client has no built-in serde strategies; strategies
  exist only in the Java SDK

### Technical Constraints

1. **Schema not in `SerializationContext`**: Record-name strategies need the Avro
   schema's `name` and optional `namespace`. Since the context carries no schema,
   the schema must be injected at strategy **construction time** — the same pattern
   already used by `AvroSerializer(schema=...)`.

2. **`ArtifactResolver` protocol must not change**: Changing the signature would
   break any user lambda or callable that satisfies the current protocol. Constructor
   injection is strictly backward-compatible.

3. **`RecordIdStrategy` groupId routing**: The Java `RecordIdStrategy` uses the
   schema's namespace as the groupId, requiring the client to target multiple groups.
   This conflicts with `ApicurioRegistryClient`'s single `group_id`. **Skip** this
   variant; implement `QualifiedRecordIdStrategy` (`{namespace}.{RecordName}`)
   against the configured group instead.

4. **Missing namespace handling**: Avro schemas at the root level may omit
   `namespace`. Strategies should handle this gracefully: if `namespace` is absent,
   fall back to `name` only (or raise `ValueError` at construction time with a clear
   message — prefer raising to failing silently at call time).

5. **100% branch coverage gate**: Every new branch must be covered by a test.

## Open Questions

- Should `RecordIdStrategy` be skipped entirely (since it requires multi-group
  routing) or included with a note that users must configure `group_id=namespace`
  manually? Recommendation: skip it; add a note in the docstring of
  `QualifiedRecordIdStrategy`.
- Should strategies validate the schema at construction time (fail fast) or
  lazily at first call? Recommendation: validate at construction time.

## Recommendations

Add two new strategy classes to `src/apicurio_serdes/avro/_strategies.py`:

### `QualifiedRecordIdStrategy`

Mirrors Confluent's `RecordNameStrategy` and Apicurio's
`QualifiedRecordIdStrategy`. Returns `"{namespace}.{RecordName}"` if the schema
has a namespace, or `"{RecordName}"` if not. Schema injected at construction.

```python
class QualifiedRecordIdStrategy:
    def __init__(self, schema: dict[str, Any]) -> None:
        name = schema.get("name")
        if not name:
            raise ValueError("schema must have a 'name' field")
        namespace = schema.get("namespace")
        self._artifact_id = f"{namespace}.{name}" if namespace else name

    def __call__(self, ctx: SerializationContext) -> str:
        return self._artifact_id
```

### `TopicRecordIdStrategy`

Mirrors Confluent's `TopicRecordNameStrategy` and Apicurio's
`TopicRecordIdStrategy`. Returns `"{topic}-{namespace}.{RecordName}"`. Schema
injected at construction; topic from context at call time.

```python
class TopicRecordIdStrategy:
    def __init__(self, schema: dict[str, Any]) -> None:
        name = schema.get("name")
        if not name:
            raise ValueError("schema must have a 'name' field")
        namespace = schema.get("namespace")
        self._record_part = f"{namespace}.{name}" if namespace else name

    def __call__(self, ctx: SerializationContext) -> str:
        return f"{ctx.topic}-{self._record_part}"
```

Both classes must be exported from `src/apicurio_serdes/avro/__init__.py` and
added to `__all__`.

Test coverage required for:

- Happy path (with namespace)
- No-namespace fallback
- `ValueError` at construction when `name` is missing
- `TopicRecordIdStrategy` with both KEY and VALUE fields

No changes needed to `AvroDeserializer`, `AsyncAvroDeserializer`,
`SerializationContext`, or `ArtifactResolver`.
