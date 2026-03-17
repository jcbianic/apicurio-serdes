# Plan: Subject / Artifact Name Strategies (2026-03-16)

## Summary

Add two new artifact resolver strategy classes — `QualifiedRecordIdStrategy`
and `TopicRecordIdStrategy` — to `apicurio-serdes`. Both derive the artifact
ID from the Avro schema's record name and namespace, injected at construction
time. They complement the existing `TopicIdStrategy` and
`SimpleTopicIdStrategy` and cover the record-name–based naming conventions
used by both Apicurio (Java) and Confluent Schema Registry. Update exports,
tests, user-guide documentation, and the changelog.

## Stakes Classification

**Level**: Low

**Rationale**: Self-contained addition to a single module
(`_strategies.py`). No changes to existing classes, no changes to
`SerializationContext`, `ArtifactResolver`, or `AvroSerializer`. Easy to
roll back by reverting the new file additions.

## Context

**Research**: [2026-03-16-subject-strategies-research.md](2026-03-16-subject-strategies-research.md)

**Web research**: Confluent Python uses call-time injection
(`strategy(ctx, record_name)`); our constructor-injection approach is
justified by the `ArtifactResolver = Callable[[SerializationContext], str]`
type alias contract. Java `RecordIdStrategy` (groupId=namespace routing) is
intentionally omitted.

**Affected Areas**:

- `src/apicurio_serdes/avro/_strategies.py` — new classes
- `src/apicurio_serdes/avro/__init__.py` — new exports
- `tests/test_strategies.py` — new test cases
- `docs/user-guide/avro-serializer.en.md` — document new strategies
- `docs/changelog.en.md` — record new public API

## Success Criteria

- [ ] `QualifiedRecordIdStrategy` and `TopicRecordIdStrategy` are importable
  from `apicurio_serdes.avro`
- [ ] Both strategies satisfy the `ArtifactResolver` protocol
- [ ] `QualifiedRecordIdStrategy` returns `"{namespace}.{name}"` when namespace
  is present, `"{name}"` when absent
- [ ] `TopicRecordIdStrategy` returns `"{topic}-{namespace}.{name}"` when
  namespace is present, `"{topic}-{name}"` when absent
- [ ] Both strategies raise `ValueError` at construction when schema has no
  `"name"` field
- [ ] All tests pass with 100% branch coverage
- [ ] User-guide documents new strategies with usage examples
- [ ] Changelog records new public API

## Implementation Steps

### Phase 1: Tests (RED)

#### Step 1.1: Write failing tests for `QualifiedRecordIdStrategy`

- **Files**: `tests/test_strategies.py`
- **Action**: Add `TestQualifiedRecordIdStrategy` class with failing tests
- **Test cases**:
  - `schema={"name": "Order", "namespace": "com.example"}` →
    `"com.example.Order"` (field irrelevant — same result for KEY and VALUE)
  - `schema={"name": "Order"}` (no namespace) → `"Order"`
  - `schema={}` (no name) → raises `ValueError` at construction
  - `schema={"name": ""}` (empty name) → raises `ValueError` at construction
- **Verify**: Tests exist and fail (`ImportError` or `AttributeError`)
- **Complexity**: Small

#### Step 1.2: Write failing tests for `TopicRecordIdStrategy`

- **Files**: `tests/test_strategies.py`
- **Action**: Add `TestTopicRecordIdStrategy` class with failing tests
- **Test cases**:
  - `schema={"name": "Order", "namespace": "com.example"}`,
    topic=`"orders"`, field=VALUE → `"orders-com.example.Order"`
  - `schema={"name": "Order", "namespace": "com.example"}`,
    topic=`"orders"`, field=KEY → `"orders-com.example.Order"`
  - `schema={"name": "Order"}` (no namespace), topic=`"orders"` →
    `"orders-Order"`
  - `schema={}` (no name) → raises `ValueError` at construction
  - `schema={"name": ""}` (empty name) → raises `ValueError` at
    construction
- **Verify**: Tests exist and fail
- **Complexity**: Small

#### Step 1.3: Write lambda/callable test for new strategies

- **Files**: `tests/test_strategies.py`
- **Action**: Assert that instances of both new classes satisfy
  `ArtifactResolver` at runtime (type check via `callable()`)
- **Test cases**:
  - `isinstance(QualifiedRecordIdStrategy(schema), ArtifactResolver)` is not
    checkable (it's a type alias), but `callable(strategy)` → `True`
  - Call the instance: `strategy(ctx)` returns a `str`
- **Verify**: Tests exist and fail
- **Complexity**: Small

### Phase 2: Implementation (GREEN)

#### Step 2.1: Implement `QualifiedRecordIdStrategy`

- **Files**: `src/apicurio_serdes/avro/_strategies.py`
- **Action**: Add `QualifiedRecordIdStrategy` class after
  `SimpleTopicIdStrategy`. Constructor extracts `name` and `namespace` from
  the schema dict, raises `ValueError` if `name` is missing or empty.
  `__call__` returns `"{namespace}.{name}"` or `"{name}"`.

  ```python
  class QualifiedRecordIdStrategy:
      def __init__(self, schema: dict[str, Any]) -> None:
          name = schema.get("name")
          if not name:
              raise ValueError(
                  "schema must have a non-empty 'name' field"
              )
          namespace = schema.get("namespace")
          self._artifact_id = (
              f"{namespace}.{name}" if namespace else name
          )

      def __call__(self, ctx: SerializationContext) -> str:
          return self._artifact_id
  ```

- **Verify**: Tests from Step 1.1 pass; `uv run pytest tests/test_strategies.py`
- **Complexity**: Small

#### Step 2.2: Implement `TopicRecordIdStrategy`

- **Files**: `src/apicurio_serdes/avro/_strategies.py`
- **Action**: Add `TopicRecordIdStrategy` class after
  `QualifiedRecordIdStrategy`. Constructor extracts `name` and `namespace`,
  raises `ValueError` if name missing or empty. `__call__` returns
  `"{topic}-{namespace}.{name}"` or `"{topic}-{name}"`.

  ```python
  class TopicRecordIdStrategy:
      def __init__(self, schema: dict[str, Any]) -> None:
          name = schema.get("name")
          if not name:
              raise ValueError(
                  "schema must have a non-empty 'name' field"
              )
          namespace = schema.get("namespace")
          self._record_part = (
              f"{namespace}.{name}" if namespace else name
          )

      def __call__(self, ctx: SerializationContext) -> str:
          return f"{ctx.topic}-{self._record_part}"
  ```

- **Verify**: Tests from Steps 1.2 and 1.3 pass;
  `uv run pytest tests/test_strategies.py`
- **Complexity**: Small

#### Step 2.3: Add type annotation import

- **Files**: `src/apicurio_serdes/avro/_strategies.py`
- **Action**: Add `Any` to the `TYPE_CHECKING` or top-level imports so the
  `dict[str, Any]` annotation resolves correctly
- **Verify**: `uv run pytest tests/test_strategies.py` passes with no import
  errors; `uv run mypy src/` (if applicable) passes
- **Complexity**: Small

#### Step 2.4: Export new strategies from `avro/__init__.py`

- **Files**: `src/apicurio_serdes/avro/__init__.py`
- **Action**: Add `QualifiedRecordIdStrategy` and `TopicRecordIdStrategy` to
  the `from apicurio_serdes.avro._strategies import (...)` block and to
  `__all__`
- **Verify**: `from apicurio_serdes.avro import QualifiedRecordIdStrategy,
  TopicRecordIdStrategy` works in a Python REPL;
  `uv run pytest tests/test_strategies.py`
- **Complexity**: Small

### Phase 3: Full Verification

#### Step 3.1: Run full test suite with coverage

- **Files**: N/A (verification only)
- **Action**: `uv run pytest --cov=apicurio_serdes --cov-fail-under=100`
- **Verify**: All tests pass; coverage stays at 100%; no regressions
- **Complexity**: Small

### Phase 4: Documentation

#### Step 4.1: Update user-guide

- **Files**: `docs/user-guide/avro-serializer.en.md`
- **Action**: Add a section documenting `QualifiedRecordIdStrategy` and
  `TopicRecordIdStrategy` alongside the existing strategy descriptions.
  Include:
  - Brief description of each strategy
  - Constructor argument (`schema: dict`)
  - Output formula (with and without namespace)
  - Note that the Java `RecordIdStrategy` (groupId=namespace routing) is not
    implemented; use `group_id` on the client instead
  - Note that each instance is schema-specific (constructor-injection
    trade-off)
  - Code example for `QualifiedRecordIdStrategy` with `auto_register=True`
- **Verify**: Markdown lints clean; content is accurate
- **Complexity**: Small

#### Step 4.2: Update changelog

- **Files**: `docs/changelog.en.md`
- **Action**: Add `QualifiedRecordIdStrategy` and `TopicRecordIdStrategy` to
  the `## Unreleased` section under "Added"
- **Verify**: Markdown lints clean
- **Complexity**: Small

## Test Strategy

### Automated Tests

| Test Case | Type | Input | Expected Output |
| --- | --- | --- | --- |
| Qualified with namespace | Unit | `{"name":"Order","namespace":"com.example"}` | `"com.example.Order"` |
| Qualified without namespace | Unit | `{"name":"Order"}` | `"Order"` |
| Qualified no name → ValueError | Unit | `{}` | `ValueError` at construction |
| Qualified empty name → ValueError | Unit | `{"name":""}` | `ValueError` at construction |
| TopicRecord with namespace, VALUE | Unit | schema + topic=`"orders"`, VALUE | `"orders-com.example.Order"` |
| TopicRecord with namespace, KEY | Unit | schema + topic=`"orders"`, KEY | `"orders-com.example.Order"` |
| TopicRecord without namespace | Unit | `{"name":"Order"}` + topic=`"orders"` | `"orders-Order"` |
| TopicRecord no name → ValueError | Unit | `{}` | `ValueError` at construction |
| TopicRecord empty name → ValueError | Unit | `{"name":""}` | `ValueError` at construction |
| callable() returns True | Unit | any valid strategy instance | `True` |
| strategy(ctx) returns str | Unit | any valid strategy instance + ctx | `str` |

### Manual Verification

- [ ] `from apicurio_serdes.avro import QualifiedRecordIdStrategy,
  TopicRecordIdStrategy` works in a fresh Python session
- [ ] Both strategies can be passed as `artifact_resolver` to `AvroSerializer`
  without errors (smoke test)

## Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| `Any` import missing in `_strategies.py` | `NameError` at runtime | Add to imports in Step 2.3 |
| Namespace-only or name-only schemas (rare Avro edge cases) | Wrong artifact ID | Validate at construction; document behavior |
| Java `RecordIdStrategy` confusion | Users expect groupId routing | Clear docstring note in both classes |

## Rollback Strategy

All changes are additive — no existing classes or interfaces are modified.
Rollback is a single `git revert` of the new commits, with no downstream
impact on existing serializers or resolvers.

## Status

- [x] Plan approved
- [x] Implementation started
- [x] Implementation complete
