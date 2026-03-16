# Plan: Artifact Resolver / Name Strategies (2026-03-13)

## Summary

Add a pluggable `artifact_resolver` parameter to `AvroSerializer` that allows
users to derive the registry artifact ID dynamically from the serialization
context (topic + field), instead of providing a static `artifact_id` string.
Provides two built-in strategies — `TopicIdStrategy` and
`SimpleTopicIdStrategy` — matching the Apicurio Java reference implementation.
Record-name strategies (which require schema introspection) are explicitly
out of scope.

## Stakes Classification

**Level**: Medium
**Rationale**: Touches the public API of `AvroSerializer` (a breaking surface),
adds a new public module, and modifies lazy schema-fetch logic. Fully testable
and backward-compatible (existing `artifact_id` callers are unaffected).

## Context

**Research**: No separate research document — design was settled in
brainstorming session (2026-03-13).
**Affected Areas**:

- `src/apicurio_serdes/avro/_serializer.py` — constructor + serialize path
- `src/apicurio_serdes/avro/_strategies.py` — new module
- `src/apicurio_serdes/avro/__init__.py` — exports
- `tests/test_strategies.py` — new test file
- `tests/test_serializer.py` — additional construction-validation tests

## Success Criteria

- [ ] `artifact_resolver` callable accepted on `AvroSerializer` as alternative
  to `artifact_id`
- [ ] Passing both or neither raises `ValueError` at construction time
- [ ] `TopicIdStrategy` returns `"{topic}-{field}"` (e.g. `"orders-value"`)
- [ ] `SimpleTopicIdStrategy` returns `"{topic}"` (e.g. `"orders"`)
- [ ] Resolver is called at first serialize, result cached — no repeated calls
- [ ] Custom callables work as resolvers (duck-typed, no ABC required)
- [ ] Existing `artifact_id` callers unchanged (full backward compatibility)
- [ ] All public symbols have type annotations and docstrings
- [ ] 100% line and branch coverage maintained

## Implementation Steps

### Phase 1: Built-in Strategies Module

#### Step 1.1: Write failing tests for strategies (RED)

- **Files**: `tests/test_strategies.py` (new)
- **Action**: Write unit tests covering all strategy behaviours. No registry
  mock needed — strategies are pure functions of `SerializationContext`.
- **Test cases**:
  - `TopicIdStrategy()(ctx(topic="orders", field=VALUE))` → `"orders-value"`
  - `TopicIdStrategy()(ctx(topic="orders", field=KEY))` → `"orders-key"`
  - `TopicIdStrategy()(ctx(topic="my-topic", field=VALUE))` → `"my-topic-value"`
  - `SimpleTopicIdStrategy()(ctx(topic="orders", field=VALUE))` → `"orders"`
  - `SimpleTopicIdStrategy()(ctx(topic="orders", field=KEY))` → `"orders"`
  - A plain `lambda ctx: "static"` satisfies the `ArtifactResolver` protocol
- **Verify**: `uv run pytest tests/test_strategies.py` — all tests collected,
  all fail with `ImportError` or `NameError`
- **Complexity**: Small

#### Step 1.2: Implement `_strategies.py` (GREEN)

- **Files**: `src/apicurio_serdes/avro/_strategies.py` (new)
- **Action**: Create module with:
  - `ArtifactResolver` type alias:
    `Callable[[SerializationContext], str]`
  - `TopicIdStrategy` callable class: returns `f"{ctx.topic}-{ctx.field.value}"`
  - `SimpleTopicIdStrategy` callable class: returns `ctx.topic`
  - Full docstrings and type annotations on all public symbols
- **Verify**: `uv run pytest tests/test_strategies.py` — all tests pass
- **Complexity**: Small

### Phase 2: Update AvroSerializer

#### Step 2.1: Write failing tests for construction validation (RED)

- **Files**: `tests/test_serializer.py`
- **Action**: Append tests for the new construction rules. No registry mock
  needed for the failure cases.
- **Test cases**:
  - Both `artifact_id` and `artifact_resolver` provided → `ValueError` at
    construction with message mentioning mutual exclusivity
  - Neither `artifact_id` nor `artifact_resolver` provided → `ValueError` at
    construction with message mentioning that one is required
  - `artifact_id` only → constructs successfully (existing behaviour)
  - `artifact_resolver` only → constructs successfully (new)
- **Verify**: `uv run pytest tests/test_serializer.py -k "resolver"` — new
  tests collected, fail with `TypeError` (unexpected keyword argument)
- **Complexity**: Small

#### Step 2.2: Write failing tests for `artifact_resolver` serialize path (RED)

- **Files**: `tests/test_serializer.py`
- **Action**: Add integration tests that serialize with a strategy.
  Use the existing `_schema_route` / `mock_registry` fixture pattern.
- **Test cases**:
  - `TopicIdStrategy()` with topic `"orders"` + `VALUE` → registry called
    with artifact_id `"orders-value"`, valid Confluent-framed bytes returned
  - `SimpleTopicIdStrategy()` with topic `"orders"` → registry called with
    `"orders"`, valid bytes returned
  - Custom `lambda ctx: "MySchema"` as resolver → equivalent to
    `artifact_id="MySchema"`
  - Serializing twice with same resolver → registry called exactly once
    (schema cached, resolver result reused)
- **Verify**: `uv run pytest tests/test_serializer.py -k "resolver"` — fail
  with `TypeError` (artifact_resolver not yet a valid param)
- **Complexity**: Small

#### Step 2.3: Update `AvroSerializer` signature and validation (GREEN)

- **Files**: `src/apicurio_serdes/avro/_serializer.py`
- **Action**:
  - Import `ArtifactResolver` from `._strategies`
  - Change `artifact_id: str` → `artifact_id: str | None = None`
  - Add `artifact_resolver: ArtifactResolver | None = None`
  - In `__init__`, validate mutual exclusivity:
    - Both provided → `ValueError`
    - Neither provided → `ValueError`
  - Store `self._artifact_resolver = artifact_resolver` (or `None`)
  - Update `self.artifact_id` assignment to handle `None`
  - Update class docstring and `Args` section
- **Verify**: Construction validation tests from Step 2.1 pass;
  serialize tests from Step 2.2 still fail (resolution not wired yet)
- **Complexity**: Small

#### Step 2.4: Wire resolver into `serialize()` (GREEN)

- **Files**: `src/apicurio_serdes/avro/_serializer.py`
- **Action**: In the lazy schema-fetch block of `serialize()`:
  - If `self._schema is None` and `self._artifact_resolver` is set, call
    `resolved = self._artifact_resolver(ctx)` and store it in
    `self.artifact_id` before the `get_schema` call
  - Schema fetch and caching logic unchanged after that point
- **Verify**: All serialize tests from Step 2.2 pass;
  `uv run pytest tests/test_serializer.py` — full suite green
- **Complexity**: Small

### Phase 3: Exports and Final Verification

#### Step 3.1: Update public exports

- **Files**: `src/apicurio_serdes/avro/__init__.py`
- **Action**: Add `TopicIdStrategy`, `SimpleTopicIdStrategy`, `ArtifactResolver`
  to imports and `__all__`
- **Verify**: `from apicurio_serdes.avro import TopicIdStrategy` works in
  a Python REPL
- **Complexity**: Small

#### Step 3.2: Full test suite and coverage gate

- **Files**: None (verification only)
- **Action**: Run `uv run pytest --cov=apicurio_serdes --cov-fail-under=100`
- **Test cases** (regressions to confirm still green):
  - All TS-001 through TS-015 BDD scenarios
  - All existing serializer unit tests
  - New strategy and resolver tests
- **Verify**: Exit code 0, 100% line and branch coverage reported
- **Complexity**: Small

## Test Strategy

### Automated Tests

| Test Case | Type | Expected Output |
| --------- | ---- | --------------- |
| TopicIdStrategy, VALUE | Unit | `"orders-value"` |
| TopicIdStrategy, KEY | Unit | `"orders-key"` |
| SimpleTopicIdStrategy | Unit | `"orders"` |
| Both params provided | Unit | `ValueError` |
| Neither param provided | Unit | `ValueError` |
| Resolver, valid data | Integration | valid bytes, 1 registry call |
| Resolver cached | Integration | registry called once |
| Lambda resolver | Integration | same as static `artifact_id` |
| Existing callers | Regression | unchanged behaviour |

### Manual Verification

- [ ] `from apicurio_serdes.avro import TopicIdStrategy, SimpleTopicIdStrategy`
  imports cleanly with no warnings
- [ ] `help(TopicIdStrategy)` renders a readable docstring

## Risks and Mitigations

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| `artifact_id` kwarg now optional | Medium | Already kwarg in all callers |
| Resolver cache stale on re-use | Low | Called once; result is fixed |
| Record strategies in scope later | Low | Defer to schema-as-input work |

## Rollback Strategy

Single-PR change. Reverting the PR restores the previous `artifact_id: str`
signature exactly. No database migrations or wire-format changes involved.

## Status

- [x] Plan approved
- [x] Implementation started
- [x] Implementation complete

### Implementation Notes

- All steps completed as planned.
- Code review (REQUEST CHANGES) led to refactoring `artifact_id` mutation: introduced
  `_resolved_artifact_id` private cache attribute, keeping `artifact_id` stable after construction.
- Security review (PASS WITH WARNINGS) led to: validating resolver return value as non-empty str,
  wrapping resolver exceptions in `SerializationError` (mirrors `to_dict`), and replacing `assert`
  with explicit `RuntimeError` (guarded with `# pragma: no cover` as unreachable defensive code).
- Final: 293 tests, 100% line and branch coverage.
