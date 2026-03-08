# Tasks: Async Registry Client

**Input**: Design documents from `/specs/003-async-registry-client/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/public-api.md, quickstart.md

**TDD**: MANDATORY per Constitution Principle III. All test tasks must be written and RED before the corresponding production code.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Exact file paths reference the project structure from plan.md

---

## Phase 1: Setup

**Purpose**: Add the async test runner dependency required by all async test functions.

- [x] T001 Add `pytest-asyncio>=0.23.0` to `[dependency-groups] dev` in pyproject.toml, set `asyncio_mode = "auto"` in `[tool.pytest.ini_options]`, and run `uv lock --upgrade-package pytest-asyncio`

---

## Phase 2: User Story 1 — Retrieve a schema asynchronously (Priority: P1) MVP

**Goal**: Deliver a working `AsyncApicurioRegistryClient` that performs a non-blocking schema fetch, maps registry errors to domain exceptions, and validates construction arguments.

**Independent Test**: Configure an async client against a `respx`-mocked registry, call `await client.get_schema(artifact_id)`, and verify the returned `CachedSchema` has the correct schema, global_id, and content_id.

### Tests (RED first)

- [x] T002 [US1] Write failing constructor validation tests (empty url → ValueError; empty group_id → ValueError) in tests/test_async_client.py [FR-008]
- [x] T003 [P] [US1] Write failing test for successful get_schema — returns CachedSchema with schema dict, global_id, and content_id parsed from response headers in tests/test_async_client.py [FR-001, FR-002, SC-001]
- [x] T004 [P] [US1] Write failing test for SchemaNotFoundError raised on HTTP 404 (group_id and artifact_id attributes populated) in tests/test_async_client.py [FR-005]
- [x] T005 [P] [US1] Write failing test for RegistryConnectionError raised on httpx.ConnectError (url attribute populated) in tests/test_async_client.py [FR-006]
- [x] T019 [P] [US1] Write failing test for RegistryConnectionError raised on unexpected HTTP status (e.g. 500) — error includes the status code and registry URL in tests/test_async_client.py [FR-013]

### Implementation (GREEN)

- [x] T006 [US1] Create src/apicurio_serdes/_async_client.py — AsyncApicurioRegistryClient with __init__ (url/group_id validation, FR-008), async get_schema (HTTP fetch via httpx.AsyncClient, response parsing, SchemaNotFoundError on 404, RegistryConnectionError on ConnectError, group_id applied to every lookup) [FR-001, FR-002, FR-005, FR-006, FR-007, FR-008]
- [x] T020 [US1] Extend get_schema HTTP error mapping: raise RegistryConnectionError (with status code + URL) for any non-200, non-404 response in src/apicurio_serdes/_async_client.py [FR-013]

**Checkpoint**: US1 tests GREEN — async schema retrieval, construction validation, and error paths all verified.

---

## Phase 3: User Stories 2+3 — Caching and Interface Parity (Priority: P2)

**Goal**: Ensure the async client contacts the registry at most once per artifact, is safe under concurrent coroutines, and mirrors the sync client interface exactly.

**Independent Test (US2)**: Call get_schema twice for the same artifact and assert `mock.calls.call_count == 1`.

**Independent Test (US3)**: Assert constructor parameter names, types, and get_schema return type match ApicurioRegistryClient; assert CachedSchema type is identical.

### Tests (RED first)

- [x] T007 [US2] Write failing cache tests: (1) same artifact_id called twice → registry contacted exactly once; (2) different artifact_ids called sequentially → each fetched independently, no cross-contamination in tests/test_async_client.py [FR-004, SC-003]
- [x] T008 [P] [US2] Write failing concurrency test: two concurrent get_schema coroutines for the same uncached artifact_id → exactly 1 HTTP request (cache stampede prevention) in tests/test_async_client.py [NFR-001]
- [x] T009 [P] [US3] Write failing interface parity test: AsyncApicurioRegistryClient constructor accepts same parameters (url, group_id) as ApicurioRegistryClient; get_schema return type is the same CachedSchema class [FR-003, SC-002, SC-004]

### Implementation (GREEN)

- [x] T010 [US2] Add asyncio.Lock + double-check cache pattern to get_schema in src/apicurio_serdes/_async_client.py: fast-path check → acquire lock → inner check → fetch → store [FR-004, NFR-001, D14]

**Checkpoint**: US2/US3 tests GREEN — caching correct, stampede prevention verified, interface parity confirmed.

---

## Phase 4: User Story 4 — Async Context Manager Lifecycle (Priority: P3)

**Goal**: Allow structured resource management via `async with`, and provide explicit `aclose()` for callers not using a context manager.

**Independent Test**: Use `async with AsyncApicurioRegistryClient(...) as client:` and assert the underlying httpx.AsyncClient is closed on exit; call `await client.aclose()` outside a context manager and assert the same.

### Tests (RED first)

- [x] T011 [US4] Write failing tests for `async with` lifecycle (__aenter__ returns self; __aexit__ closes the underlying httpx.AsyncClient) and for explicit `await client.aclose()` in tests/test_async_client.py [FR-009, FR-010]
- [x] T021 [P] [US4] Write failing test for RuntimeError raised when get_schema is called after aclose() or after an async with block exits in tests/test_async_client.py [FR-012]

### Implementation (GREEN)

- [x] T012 [US4] Implement `async __aenter__`, `async __aexit__`, and `async aclose()` methods in src/apicurio_serdes/_async_client.py [FR-009, FR-010]
- [x] T022 [US4] Add closed-client guard to get_schema in src/apicurio_serdes/_async_client.py: track closed state in aclose()/__aexit__ and raise RuntimeError("client is closed") at the start of get_schema if closed [FR-012]

**Checkpoint**: US4 tests GREEN — context manager lifecycle, explicit close, and closed-client guard all verified.

---

## Phase 5: Package Export

**Purpose**: Make AsyncApicurioRegistryClient importable from the top-level package (FR-011).

### Tests (RED first)

- [x] T013 Write failing test asserting `from apicurio_serdes import AsyncApicurioRegistryClient` succeeds and the imported name is the correct class in tests/test_async_client.py [FR-011]

### Implementation (GREEN)

- [x] T014 Update src/apicurio_serdes/__init__.py: add `from apicurio_serdes._async_client import AsyncApicurioRegistryClient` and include `"AsyncApicurioRegistryClient"` in `__all__` [FR-011]

**Checkpoint**: Top-level import test GREEN — AsyncApicurioRegistryClient publicly accessible alongside ApicurioRegistryClient.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Type safety, coverage gate, and documentation — constitutional quality requirements.

- [x] T015 [P] Run `mypy --strict src/apicurio_serdes/_async_client.py` and fix all type annotation gaps; add or verify complete docstrings (parameters, return values, raised exceptions) on all public symbols: AsyncApicurioRegistryClient, get_schema, aclose, __aenter__, __aexit__
- [x] T016 [P] Run `pytest --cov-fail-under=100` and fill any line or branch coverage gaps in src/apicurio_serdes/_async_client.py
- [x] T017 [P] [DOCS] Create docs/user-guide/async-client.md — async usage guide covering basic fetch, context manager pattern, FastAPI lifespan integration, and side-by-side sync/async comparison (per Constitution Development Workflow)
- [x] T018 Run quickstart.md validation — execute all code examples in specs/003-async-registry-client/quickstart.md against the implemented client and verify output

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) ──→ Phase 2 (US1/P1) ──→ Phase 3 (US2+US3/P2) ──→ Phase 4 (US4/P3) ──→ Phase 5 (Export) ──→ Phase 6 (Polish)
```

### Critical Path

T001 → T002 → T006 → T007 → T010 → T011 → T012 → T013 → T014 → T016 → T018

### Parallel Batches

| Batch | Tasks | Phase |
|-------|-------|-------|
| A | T003, T004, T005, T019 | Phase 2 tests (after T002 establishes conftest patterns) |
| B | T008, T009 | Phase 3 tests (after T007 establishes cache test pattern) |
| C | T015, T016, T017 | Phase 6 polish |
| D | T021 | Phase 4 tests (parallel with T011) |

### Story Independence

- US1 (Phase 2): depends on Phase 1 only; foundational — all other stories build on this
- US2 (Phase 3): depends on US1 (T006 class skeleton must exist for cache extension)
- US3 (Phase 3): depends on US1 (class must exist to verify parity); tests parallel with US2 tests
- US4 (Phase 4): depends on US1 (class must exist to add context manager methods)
- No priority inversions detected

---

## Summary

| Metric | Value |
|--------|-------|
| Total tasks | 22 |
| Phase 1 (Setup) | 1 |
| Phase 2 (US1/P1) | 7 |
| Phase 3 (US2+US3/P2) | 4 |
| Phase 4 (US4/P3) | 4 |
| Phase 5 (Export) | 2 |
| Phase 6 (Polish) | 4 |
| Parallel opportunities | 4 batches |
| MVP scope | Phases 1–2 (6 tasks) deliver core async schema retrieval |

---

## Notes

- [P] tasks = different files or independent test functions with no shared state
- [Story] label maps task to specific user story for traceability
- TDD is MANDATORY: write tests first (RED), then implement (GREEN), then refactor
- Stop at any checkpoint to validate story independently
- Implementation auto-commits after each task
