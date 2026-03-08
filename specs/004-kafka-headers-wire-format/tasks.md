# Tasks: WireFormat.KAFKA_HEADERS Support

**Feature**: `004-kafka-headers-wire-format`
**Input**: `specs/004-kafka-headers-wire-format/`
**Prerequisites**: plan.md ✓, spec.md ✓, data-model.md ✓, research.md ✓, contracts/ ✓, testify ✓
**BDD Scenarios**: `specs/004-kafka-headers-wire-format/tests/features/` — 3 feature files, 18 scenarios
**Tech Stack**: Python 3.10+, pytest, pytest-bdd, pytest-cov, fastavro, respx

## Format: `[ID] [P?] [Story?] Description`

- `[P]` = parallelizable (different files, no shared state)
- `[USn]` = user story mapping (omitted for Setup / Foundational / Polish tasks)
- Test IDs: explicit comma-separated lists — never prose ranges

---

## Phase 1: Setup

**Purpose**: BDD test infrastructure — one-time setup before any story implementation.

- [ ] T001 Set up pytest-bdd step definition modules directory at `tests/step_defs/` and register feature file paths from `specs/004-kafka-headers-wire-format/tests/features/` in `conftest.py` or `pyproject.toml`

---

## Phase 2: Foundational — Shared Entities (blocks all stories)

**Purpose**: `WireFormat` enum, `SerializedMessage` dataclass, and `AvroSerializer`
CONFLUENT_PAYLOAD refactor. These entities are shared prerequisites for all user stories.

**Priority note**: US2 (P2) and US3 (P3) implementation work is grouped here as a
technical prerequisite for US1 (P1) KAFKA_HEADERS. Plan §Implementation Strategy Phase
1+2 explicitly accounts for this ordering.

### TDD-First: Write Failing Tests (RED)

- [ ] T002 [P] Write failing step definitions for WireFormat API scenarios [TS-020, TS-021, TS-022, TS-023, TS-024] in `tests/step_defs/test_wire_format_api.py`
- [ ] T003 [P] Write failing unit tests for `WireFormat` enum members and `SerializedMessage` frozen dataclass in `tests/test_serialization.py`
- [ ] T004 [P] Write failing step definitions for CONFLUENT_PAYLOAD compatibility scenarios [TS-010, TS-011, TS-012, TS-013, TS-014] in `tests/step_defs/test_confluent_payload_compat.py`
- [ ] T005 [P] Write failing unit tests for `AvroSerializer` `wire_format` parameter and `serialize()` CONFLUENT_PAYLOAD path in `tests/test_serializer.py`

### Implementation: GREEN (after T002–T005 are confirmed RED)

- [ ] T006 Implement `WireFormat(enum.Enum)` with `CONFLUENT_PAYLOAD` and `KAFKA_HEADERS` members and `SerializedMessage(payload: bytes, headers: dict[str, bytes])` frozen dataclass in `src/apicurio_serdes/serialization.py` [passes TS-020, TS-021]
- [ ] T007 Re-export `WireFormat` from `src/apicurio_serdes/__init__.py` and add to `__all__` (FR-002) [passes TS-020]
- [ ] T008 Add `wire_format: WireFormat = WireFormat.CONFLUENT_PAYLOAD` parameter to `AvroSerializer.__init__` in `src/apicurio_serdes/avro/_serializer.py` [passes TS-022, TS-023, TS-024]
- [ ] T009 Implement `AvroSerializer.serialize(data, ctx) -> SerializedMessage` method — CONFLUENT_PAYLOAD branch: framed bytes with `0x00` + 4-byte big-endian schema ID + Avro payload, empty `headers` dict — in `src/apicurio_serdes/avro/_serializer.py` [passes TS-010, TS-011, TS-012]
- [ ] T010 Refactor `AvroSerializer.__call__` to delegate to `serialize()` and return `.payload` in `src/apicurio_serdes/avro/_serializer.py` [passes TS-013, TS-014]

**Checkpoint**: Foundational complete — US2 scenarios [TS-010, TS-011, TS-012, TS-013, TS-014] and US3 scenarios [TS-020, TS-021, TS-022, TS-023, TS-024] all pass. US1 KAFKA_HEADERS implementation can begin.

---

## Phase 3: User Story 1 — KAFKA_HEADERS Serialization (Priority: P1) — MVP

**Goal**: Produce Avro messages where the schema identifier is carried in Kafka message
headers rather than embedded in the message bytes.

**Independent Test**: Configure `AvroSerializer(wire_format=WireFormat.KAFKA_HEADERS)`,
call `.serialize(data, ctx)`, verify (a) payload has no magic byte or schema ID prefix,
(b) `headers` contains exactly one entry with Apicurio's native header name and an
8-byte big-endian signed long value.

### TDD-First: Write Failing Tests (RED)

- [ ] T011 [P] [US1] Write failing step definitions for KAFKA_HEADERS scenarios [TS-001, TS-002, TS-003, TS-004, TS-005, TS-006, TS-007, TS-008] in `tests/step_defs/test_kafka_headers_serialization.py`
- [ ] T012 [P] [US1] Write failing byte-level tests for KAFKA_HEADERS header name lookup (4 field/use_id combinations) and `struct.pack(">q", schema_id)` value encoding in `tests/test_wire_format.py`

### Implementation: GREEN (after T011–T012 are confirmed RED)

- [ ] T013 [US1] Implement KAFKA_HEADERS branch in `AvroSerializer.serialize()` in `src/apicurio_serdes/avro/_serializer.py`: raw Avro binary payload (no magic byte, no schema ID prefix), header name lookup table for all 4 `MessageField` × `use_id` combinations (`apicurio.{key|value}.{globalId|contentId}`), `struct.pack(">q", schema_id)` 8-byte big-endian signed long header value, `SchemaNotFoundError` raised before any payload or headers are produced for missing artifacts [passes TS-001, TS-002, TS-003, TS-004, TS-005, TS-006, TS-007]
- [ ] T014 [US1] Verify schema caching preserved in KAFKA_HEADERS mode: assert exactly 1 HTTP call to registry for 1000 consecutive `serialize()` calls against the same artifact in `tests/test_wire_format.py` [passes TS-008]

**Checkpoint**: US1 complete — all 8 KAFKA_HEADERS scenarios pass. Feature is functional end-to-end.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Quality gates, documentation, and final validation before release.

- [ ] T015 [P] Run `mypy --strict` on `src/apicurio_serdes/serialization.py` and `src/apicurio_serdes/avro/_serializer.py` and fix any missing type annotations or signature gaps
- [ ] T016 [P] Run `uv run pytest --cov=src --cov-branch --cov-fail-under=100` and verify 100% line and branch coverage gate passes for all modified modules
- [ ] T017 [DOCS] Write `docs/user-guide/kafka-headers-wire-format.md` user guide page for KAFKA_HEADERS mode and update API reference docstrings in `src/apicurio_serdes/serialization.py` (for `WireFormat`, `SerializedMessage`) and `src/apicurio_serdes/avro/_serializer.py` (for `AvroSerializer.wire_format`, `AvroSerializer.serialize()`)
- [ ] T018 Validate `specs/004-kafka-headers-wire-format/quickstart.md` code examples run correctly with `uv run python` against the installed package

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on T001 — **BLOCKS all user stories**
- **US1 (Phase 3)**: Depends on Foundational completion (T010 done) — **BLOCKS Polish**
- **Polish (Final)**: Depends on US1 completion (T014 done)

### Parallel Opportunities

**Foundational test-writing (T002–T005)**: All target different files — run in parallel:
```
T001 → [T002 | T003 | T004 | T005] → T006 → T007 → T008 → T009 → T010
```

**US1 test-writing (T011–T012)**: Step defs and byte-level tests target different files — run in parallel:
```
T010 → [T011 | T012] → T013 → T014
```

**Polish (T015–T016)**: mypy and coverage are independent — run in parallel:
```
T014 → [T015 | T016 | T017] → T018
```

### Critical Path

```
T001 → T003 → T006 → T007 → T008 → T009 → T010 → T011 → T013 → T014 → T017 → T018
```
(12 tasks on the critical path; T015/T016 run parallel to T017 in the Polish phase)

### Dependency Graph

```
T001
 ├─ T002 [P] ─────────────────────────────────────────┐
 ├─ T003 [P] ──────────────────────── T006 ───────────┤
 ├─ T004 [P] ─────────────────────────────────────────┤──→ T007 → T008 → T009 → T010
 └─ T005 [P] ─────────────────────────────────────────┘                            │
                                                                          ┌─ T011 [P] ─┐
                                                                          └─ T012 [P] ─┘──→ T013 → T014
                                                                                                      │
                                                                                          ┌─ T015 [P] ─┤
                                                                                          ├─ T016 [P]  │
                                                                                          └─ T017 ─────┘──→ T018
```

---

## Summary

| Phase | Tasks | User Story | Scenarios |
|-------|-------|------------|-----------|
| Setup | T001 | — | — |
| Foundational | T002–T010 | US2, US3 (prereq) | [TS-010, TS-011, TS-012, TS-013, TS-014, TS-020, TS-021, TS-022, TS-023, TS-024] |
| US1 (P1) | T011–T014 | US1 | [TS-001, TS-002, TS-003, TS-004, TS-005, TS-006, TS-007, TS-008] |
| Polish | T015–T018 | — | all |
| **Total** | **18** | | **18 scenarios** |

**MVP scope**: T001–T014 deliver the complete feature (KAFKA_HEADERS functional, backward
compat preserved, WireFormat API in place). T015–T018 are required for release quality.

---

## Notes

- **TDD discipline** (Constitution Principle III — NON-NEGOTIABLE): Confirm RED before GREEN in each phase. No production code without a preceding failing test.
- **Assertion integrity**: Never modify `.feature` files — write step definitions and fix production code to match scenarios as written.
- **Coverage gate**: 100% line + branch (`coverage.py --branch`) is a hard quality gate enforced by CI.
- **DOCS task**: T017 is constitutionally mandated — every feature must include a `[DOCS]` task.
- **No new runtime dependencies**: All new symbols (`WireFormat`, `SerializedMessage`, `struct.pack`) use Python stdlib only.
