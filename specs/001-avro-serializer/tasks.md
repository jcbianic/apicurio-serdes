# Tasks: Avro Serializer (Producer Side)

**Input**: Design documents from `/specs/001-avro-serializer/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/public-api.md ✓
**Test Specs**: 18 BDD scenarios in `specs/001-avro-serializer/tests/features/` (TS-001 – TS-018)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[USn]**: User story tag — required for all user story implementation tasks
- **TDD order enforced**: step definitions FIRST (RED — verify pytest exits non-zero), production code SECOND (GREEN)

## Plan Readiness

| Item | Status | Notes |
|------|--------|-------|
| Language/Version | ✓ | Python 3.10+ |
| Tech stack | ✓ | fastavro ≥ 1.9.0, httpx ≥ 0.27.0, pytest-bdd added (required by .feature files) |
| User stories | ✓ | All 3 have acceptance criteria and mapped .feature files |
| Shared entities | ✓ | SerializationContext, MessageField, error classes, ApicurioRegistryClient → Phase 2 Foundational |
| Feature files | ✓ | 4 .feature files with 18 test specs in `specs/001-avro-serializer/tests/features/` |

> **Note**: `pytest-bdd` is not in plan.md (plan predates testify). It must be added to `pyproject.toml` per phase-discipline rule: .feature files require a BDD runner.

---

## Phase 1: Setup

**Purpose**: Project initialization — no user stories can begin until Phase 1 is complete

- [x] T001 Create `pyproject.toml` with hatchling build config, runtime deps (fastavro≥1.9.0, httpx≥0.27.0), dev deps (pytest≥8.0.0, pytest-bdd, pytest-cov≥5.0.0, respx≥0.21.0, mypy≥1.10.0, ruff≥0.5.0), and tool sections (ruff, mypy strict, pytest `--cov=src/apicurio_serdes --cov-branch --cov-fail-under=100 --feature-base-dir=specs/001-avro-serializer/tests/features`)
- [x] T002 Create `src/apicurio_serdes/` package layout: `__init__.py`, `serialization.py`, `_client.py`, `_errors.py`, `py.typed`, `avro/__init__.py`, `avro/_serializer.py` (all empty stubs so imports resolve)
- [x] T003 Create `tests/` package: `conftest.py` with shared fixtures (respx mock router, sample Avro schema JSON for `UserEvent` record, sample valid and invalid dicts), empty `tests/__init__.py`

**Checkpoint**: Repository skeleton in place — `uv run pytest` can discover and fail tests

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core entities shared across all user stories — MUST be complete before any user story phase begins

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 [P] [TDD-RED] Write step definitions for TS-009 in `tests/test_serialization.py` referencing `specs/001-avro-serializer/tests/features/avro_serialization.feature` — verify `pytest tests/test_serialization.py` exits non-zero (depends on T003)
- [x] T005 [P] [TDD-RED] Write step definitions for TS-008 in `tests/test_client.py` referencing `specs/001-avro-serializer/tests/features/avro_serialization.feature` — verify `pytest tests/test_client.py` exits non-zero (depends on T003)
- [x] T006 Implement `MessageField` enum and `SerializationContext` dataclass with full type annotations and docstrings in `src/apicurio_serdes/serialization.py` to pass TS-009 (depends on T004)
- [x] T007 [P] Implement `SchemaNotFoundError`, `SerializationError`, `RegistryConnectionError` with full type annotations and docstrings in `src/apicurio_serdes/_errors.py` (depends on T005)
- [x] T008 Implement `ApicurioRegistryClient` with httpx sync session, dict-based schema cache keyed by `(group_id, artifact_id)`, `X-Registry-GlobalId` and `X-Registry-ContentId` header parsing, 404 → `SchemaNotFoundError`, network error → `RegistryConnectionError` in `src/apicurio_serdes/_client.py` to pass TS-008 (depends on T006, T007)
- [x] T009 Re-export `ApicurioRegistryClient` from `src/apicurio_serdes/__init__.py` (depends on T008)

**Checkpoint**: Foundational complete — `SerializationContext`, `MessageField`, all error types, and `ApicurioRegistryClient` are implemented; `pytest tests/test_serialization.py tests/test_client.py` passes TS-008, TS-009

---

## Phase 3: User Story 1 — Serialize Python dict to Confluent-framed Avro bytes (Priority: P1) MVP

**Goal**: End-to-end serialization from a Python dict to Confluent wire format bytes using a schema from Apicurio Registry
**Independent Test**: Configure `AvroSerializer` against a mock registry (respx), call `serializer(dict, ctx)`, verify `0x00` + 4-byte schema ID + valid Avro payload

### TDD — Write step definitions FIRST (RED phase)

- [x] T010 [TDD-RED] [US1] Write step definitions for TS-001, TS-002, TS-003, TS-004, TS-005, TS-006, TS-007 in `tests/test_serializer.py` referencing `specs/001-avro-serializer/tests/features/avro_serialization.feature` — verify `pytest tests/test_serializer.py` exits non-zero (depends on T008, T009)
- [x] T011 [P] [TDD-RED] Write step definitions for TS-016, TS-017, TS-018 in `tests/test_wire_format.py` referencing `specs/001-avro-serializer/tests/features/wire_format.feature` — verify `pytest tests/test_wire_format.py` exits non-zero (depends on T008, T009)

### Implementation (GREEN phase)

- [x] T012 [US1] Implement `AvroSerializer.__init__` and `__call__` in `src/apicurio_serdes/avro/_serializer.py`: apply `to_dict` if provided, delegate schema fetch to `registry_client.get_schema()`, encode with `fastavro.schemaless_writer`, prepend Confluent wire header (`b'\x00' + struct.pack('>I', schema_id)`) — to pass TS-001, TS-002, TS-003, TS-004, TS-005, TS-016, TS-018 (depends on T010, T011)
- [x] T013 [US1] Add strict mode validation to `AvroSerializer.__call__` in `src/apicurio_serdes/avro/_serializer.py`: when `strict=True`, reject extra fields not present in schema before encoding — to pass TS-006, TS-007 (depends on T012)
- [x] T014 [US1] Implement `use_id="contentId"` path in `AvroSerializer.__call__` in `src/apicurio_serdes/avro/_serializer.py`: use `CachedSchema.content_id` as the 4-byte wire format ID when `use_id="contentId"` — to pass TS-017 (depends on T012)
- [x] T015 Re-export `AvroSerializer` from `src/apicurio_serdes/avro/__init__.py` (depends on T012)

**Checkpoint**: US1 complete — `AvroSerializer` serializes dicts to valid Confluent-framed Avro bytes; TS-001, TS-002, TS-003, TS-004, TS-005, TS-006, TS-007, TS-016, TS-017, TS-018 GREEN; SC-001 satisfied

---

## Phase 4: User Story 2 — Schema caching prevents redundant registry lookups (Priority: P2)

**Goal**: Verify that `ApicurioRegistryClient` never makes more than one HTTP call per unique `artifact_id`, including under concurrent access
**Independent Test**: Serialize two messages with the same `artifact_id` and assert registry called exactly once; run concurrent serializers for the same artifact and assert exactly one HTTP call

### TDD — Write step definitions FIRST (RED phase)

- [x] T016 [TDD-RED] [US2] Write step definitions for TS-010, TS-011, TS-012 in `tests/test_client.py` referencing `specs/001-avro-serializer/tests/features/schema_caching.feature` — verify `pytest tests/test_client.py` exits non-zero for the new scenarios (depends on T012)

### Implementation (GREEN phase)

- [x] T017 [US2] Add `threading.RLock` guard to `ApicurioRegistryClient.get_schema()` in `src/apicurio_serdes/_client.py` to ensure at most one HTTP call per `artifact_id` under concurrent access (NFR-001) — to pass TS-010, TS-011, TS-012 (depends on T016)

**Checkpoint**: US2 complete — schema cache is thread-safe; TS-010, TS-011, TS-012 GREEN; SC-003 satisfied (1 HTTP call per 1,000 messages with same `artifact_id`)

---

## Phase 5: User Story 3 — Custom object-to-dict transformation via to_dict hook (Priority: P3)

**Goal**: Allow callers to serialize domain objects directly by providing a `to_dict` callable
**Independent Test**: Create `AvroSerializer` with `to_dict=vars`, serialize a simple object, verify output bytes match direct dict serialization

### TDD — Write step definitions FIRST (RED phase)

- [x] T018 [TDD-RED] [US3] Write step definitions for TS-013, TS-014, TS-015 in `tests/test_serializer.py` referencing `specs/001-avro-serializer/tests/features/to_dict_hook.feature` — verify `pytest tests/test_serializer.py` exits non-zero for the new scenarios (depends on T012)

### Implementation (GREEN phase)

- [x] T019 [US3] Implement `to_dict` invocation and `SerializationError` wrapping in `AvroSerializer.__call__` in `src/apicurio_serdes/avro/_serializer.py`: call `self.to_dict(data, ctx)` before encoding; catch any raised exception and re-raise as `SerializationError(__cause__)` per FR-013 — to pass TS-013, TS-014, TS-015 (depends on T018)

**Checkpoint**: US3 complete — `to_dict` hook transforms domain objects; TS-013, TS-014, TS-015 GREEN

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Quality gates, type safety, and final validation — apply after all desired user story phases are complete

- [x] T020 [P] Run `mypy --strict src/` and fix all type annotation gaps and incomplete docstrings across all public symbols in `src/apicurio_serdes/`
- [x] T021 [P] Run `pytest --cov=src/apicurio_serdes --cov-branch --cov-fail-under=100` and add missing step definitions or tests for any uncovered branch in `src/`
- [x] T022 [P] Run `ruff check . && ruff format --check .` and fix all linting and formatting violations across `src/` and `tests/`
- [ ] T023 Verify `quickstart.md` code examples execute correctly end-to-end against mock registry in test suite; confirm SC-001 (no custom HTTP or Avro library calls at call site)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Requires Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Requires Phase 2 — MVP deliverable; BLOCKS US3
- **US2 (Phase 4)**: Requires Phase 2 (client) and Phase 3 (AvroSerializer for fixtures)
- **US3 (Phase 5)**: Requires Phase 3 (AvroSerializer `__call__` must exist)
- **Polish (Phase 6)**: Requires all desired story phases complete

### Parallel Opportunities

**Phase 2** (once T003 done):
- T004 ‖ T005 (different test files)
- T006 ‖ T007 (different source files, no inter-dependency)

**Phase 3** (once T008, T009 done):
- T010 ‖ T011 (different test files, both RED phase)
- T013 ‖ T014 (different aspects of `_serializer.py` — both depend on T012; verify no merge conflict)

**Phase 4 and Phase 5** (once T012 done):
- T016 ‖ T018 (different test sections, depend only on T012)
- T017 ‖ T019 (different source files, after respective step defs)

**Phase 6**:
- T020 ‖ T021 ‖ T022 (independent tools, independent files)

### Critical Path

```
T001→T002→T003
         ↓
    T004‖T005
         ↓
    T006‖T007
         ↓
        T008→T009
               ↓
          T010‖T011
               ↓
              T012
               ↓
          T013‖T014‖T015
               ↓
    T016‖T017‖T018‖T019
               ↓
    T020‖T021‖T022→T023
```

### Task Count

| Phase | Tasks | Notes |
|-------|-------|-------|
| 1 — Setup | 3 | T001–T003 |
| 2 — Foundational | 6 | T004–T009 |
| 3 — US1 (P1) MVP | 6 | T010–T015 |
| 4 — US2 (P2) | 2 | T016–T017 |
| 5 — US3 (P3) | 2 | T018–T019 |
| 6 — Polish | 4 | T020–T023 |
| **Total** | **23** | |

---

## Notes

- `[P]` = safe to parallelize — different files, no shared state
- TDD order is non-negotiable per `CONSTITUTION.md` Principle III — step definitions run RED before any implementation
- `.feature` files in `specs/001-avro-serializer/tests/features/` are the canonical test specs — do **NOT** modify them; re-run `/iikit-04-testify` if requirements change
- `CachedSchema` is an internal value object; it must carry both `global_id` (from `X-Registry-GlobalId` header) and `content_id` (from `X-Registry-ContentId` header) to support both `use_id` modes (FR-010)
- MVP scope = Phase 1 + Phase 2 + Phase 3 (US1): delivers SC-001 and SC-002
- Each checkpoint is a valid delivery state where all prior test specs are GREEN
