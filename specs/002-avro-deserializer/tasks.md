# Tasks: Avro Deserializer (Consumer Side)

**Input**: Design documents from `/specs/002-avro-deserializer/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/public-api.md, quickstart.md, .feature files

**TDD**: MANDATORY per Constitution Principle III. All test tasks must be implemented and RED before the corresponding production code.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Exact file paths reference the project structure from plan.md

---

## Phase 1: Setup

**Purpose**: BDD infrastructure for .feature file execution

- [x] T001 Add pytest-bdd step definition scaffolding in tests/features/ and configure pytest to discover .feature files from specs/002-avro-deserializer/tests/features/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Error classes and client methods shared by ALL user stories. MUST be complete before any story implementation begins.

### Tests (RED first)

- [x] T002 [P] Write tests for DeserializationError construction, message, and cause chaining in tests/test_errors.py [TS-003, TS-005, TS-006, TS-007, TS-015]
- [x] T003 [P] Write tests for SchemaNotFoundError.from_id classmethod (message format, id_type/id_value attributes) in tests/test_errors.py [TS-004]
- [x] T004 [P] Write tests for ApicurioRegistryClient.get_schema_by_global_id (cache miss, cache hit, 404, network error) in tests/test_client.py [TS-017, FR-007, FR-010, FR-012]
- [x] T005 [P] Write tests for ApicurioRegistryClient.get_schema_by_content_id (cache miss, cache hit, 404, network error) in tests/test_client.py [TS-016, FR-007, FR-010, FR-012]

### Implementation (GREEN)

- [x] T006 [P] Implement DeserializationError in src/apicurio_serdes/_errors.py [FR-003, FR-004, FR-009, FR-011]
- [x] T007 [P] Implement SchemaNotFoundError.from_id classmethod in src/apicurio_serdes/_errors.py [FR-010]
- [x] T008 Add _id_cache dict and get_schema_by_global_id method to ApicurioRegistryClient in src/apicurio_serdes/_client.py [FR-007, FR-010, FR-012]
- [x] T009 Add get_schema_by_content_id method to ApicurioRegistryClient in src/apicurio_serdes/_client.py (depends on T008 for _id_cache) [FR-007, FR-010, FR-012]

**Checkpoint**: All foundational tests GREEN. Error classes and client ID-based lookups verified.

---

## Phase 3: User Story 1 — Deserialize Confluent-framed Avro bytes to a Python dict (Priority: P1) MVP

**Goal**: Core end-to-end deserialization: wire format parsing, schema resolution, Avro decoding, error handling.

**Independent Test**: Feed Confluent-framed Avro bytes to AvroDeserializer and verify the returned dict matches the original data.

### Tests (RED first)

- [x] T010 [P] [US1] Write BDD step definitions for avro_deserialization.feature scenarios in tests/features/test_avro_deserialization.py [TS-001, TS-002, TS-003, TS-004, TS-005, TS-006, TS-007, TS-008, TS-009]
- [x] T011 [P] [US1] Write BDD step definitions for wire_format.feature contract scenarios (default contentId, callable interface) in tests/features/test_wire_format.py [TS-016, TS-018]
- [x] T012 [P] [US1] Write unit tests for AvroDeserializer.__init__ and __call__ in tests/test_deserializer.py covering: valid decode, bad magic byte, short input, unknown ID, corrupt payload [FR-001, FR-002, FR-003, FR-004, FR-005, FR-011]

### Implementation

- [x] T013 [US1] Implement AvroDeserializer in src/apicurio_serdes/avro/_deserializer.py (depends on T006, T007, T008, T009) [FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-011]
- [x] T014 [US1] Re-export AvroDeserializer from src/apicurio_serdes/avro/__init__.py
- [x] T015 [US1] Export DeserializationError from src/apicurio_serdes/_errors.py (verify public import path)

**Checkpoint**: US1 complete — valid deserialization, all error paths, wire format contract, round-trip test all GREEN.

---

## Phase 4: User Story 2 — Schema caching prevents redundant registry lookups (Priority: P2)

**Goal**: Verify that the caching built into the client (Phase 2) and deserializer's _parsed_cache work correctly under sequential and concurrent access.

**Independent Test**: Deserialize two messages with the same schema ID and assert the registry was contacted exactly once.

### Tests (RED first)

- [ ] T016 [P] [US2] Write BDD step definitions for schema_caching.feature scenarios in tests/features/test_schema_caching.py [TS-010, TS-011, TS-012]
- [x] T017 [P] [US2] Write BDD step definition for wire_format.feature globalId scenario in tests/features/test_wire_format.py [TS-017]

### Implementation

- [x] T018 [US2] Implement _parsed_cache in AvroDeserializer for fastavro parsed schema caching in src/apicurio_serdes/avro/_deserializer.py (depends on T013) [FR-007, NFR-001]
- [ ] T019 [US2] Write thread-safety test for concurrent deserialization with same schema ID in tests/test_deserializer.py [TS-012, NFR-001]

**Checkpoint**: US2 complete — sequential caching, multi-schema caching, and thread safety all GREEN.

---

## Phase 5: User Story 3 — Custom dict-to-object transformation via from_dict hook (Priority: P3)

**Goal**: Optional post-decode transformation hook for domain objects.

**Independent Test**: Create AvroDeserializer with a from_dict hook, deserialize a message, verify the return is the domain object.

### Tests (RED first)

- [ ] T020 [P] [US3] Write BDD step definitions for from_dict_hook.feature scenarios in tests/features/test_from_dict_hook.py [TS-013, TS-014, TS-015]
- [ ] T021 [P] [US3] Write unit tests for from_dict hook in tests/test_deserializer.py (callable applied, absent callable returns dict, exception wrapping) [FR-008, FR-009]

### Implementation

- [x] T022 [US3] Implement from_dict hook logic in AvroDeserializer.__call__ in src/apicurio_serdes/avro/_deserializer.py (depends on T013) [FR-008, FR-009]

**Checkpoint**: US3 complete — from_dict applied, identity default, exception wrapping all GREEN.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Integration validation, coverage gate, documentation

- [ ] T023 Run full round-trip integration test (serialize + deserialize) and verify SC-002, SC-005
- [ ] T024 Run 100% line + branch coverage gate and fix any gaps
- [ ] T025 Run mypy strict type checking and fix any annotation gaps
- [ ] T026 [P] Verify API naming matches confluent-kafka conventions (SC-004 — side-by-side comparison)
- [ ] T027 [P] [DOCS] Update docs/user-guide/ with deserializer usage, round-trip example, and error handling (per Constitution Development Workflow)
- [ ] T028 [P] [DOCS] Ensure all public API docstrings are complete and current for AvroDeserializer, DeserializationError, new client methods
- [ ] T029 Run quickstart.md validation — execute all code examples and verify output

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) ──→ Phase 2 (Foundational) ──→ Phase 3 (US1/P1) ──→ Phase 4 (US2/P2) ──→ Phase 5 (US3/P3) ──→ Phase 6 (Polish)
```

### Critical Path

T001 → T002..T005 (parallel) → T006..T009 → T010..T012 (parallel) → T013 → T014,T015 → T016,T017 (parallel) → T018 → T019 → T020,T021 (parallel) → T022 → T023..T029

### Parallel Batches

| Batch | Tasks | Phase |
|-------|-------|-------|
| A | T002, T003, T004, T005 | Phase 2 tests |
| B | T006, T007 | Phase 2 error impl |
| C | T010, T011, T012 | Phase 3 tests |
| D | T016, T017 | Phase 4 tests |
| E | T020, T021 | Phase 5 tests |
| F | T026, T027, T028 | Phase 6 polish |

### Story Independence

- US1 (Phase 3) depends on Foundational (Phase 2) only
- US2 (Phase 4) depends on US1 (T013 for _parsed_cache)
- US3 (Phase 5) depends on US1 (T013 for __call__ implementation)
- No priority inversions detected

---

## Summary

| Metric | Value |
|--------|-------|
| Total tasks | 29 |
| Phase 1 (Setup) | 1 |
| Phase 2 (Foundational) | 8 |
| Phase 3 (US1/P1) | 6 |
| Phase 4 (US2/P2) | 4 |
| Phase 5 (US3/P3) | 3 |
| Phase 6 (Polish) | 7 |
| Parallel opportunities | 6 batches |
| MVP scope | Phases 1-3 (15 tasks) deliver core deserialization |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- TDD is MANDATORY: write tests first, verify RED, then implement GREEN
- Implementation auto-commits after each task
- Stop at any checkpoint to validate story independently
