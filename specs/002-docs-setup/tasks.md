# Tasks: docs-setup

**Input**: Design documents from `specs/002-docs-setup/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓
**Feature branch**: `007-docs-setup`

**Tests**: Feature files in `specs/002-docs-setup/tests/features/` (TS-001–TS-016). Tasks reference specific scenario IDs.

**Organization**: Infrastructure → US1 (P1) → US2 (P2) → US3 (P3) → US5 (P5) + How-to Guides → US4 (P4, French translations) → Validation.

**Note on TDD applicability**: Per the constitution and plan.md constitution check, this feature contains no production code. The quality gate is `mkdocs build --strict` (zero warnings). Feature scenarios (TS-001–TS-016) serve as acceptance criteria for content completeness, not as executable automated tests. No step definitions are required.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[USn]**: Which user story this task belongs to
- Paths are relative to repository root

---

## Phase 1: Infrastructure Setup

**Purpose**: i18n infrastructure, file renames, and configuration that ALL content tasks depend on.

**CRITICAL**: No content tasks can begin until this phase is complete.

- [x] T001 [P] Add `mkdocs-static-i18n[material]>=1.3.0,<2.0` to `docs` dependency group in `pyproject.toml`
- [x] T002 [P] Rename existing docs to `.en.md` suffix: `docs/index.md` → `docs/index.en.md`, `docs/getting-started/installation.md` → `docs/getting-started/installation.en.md`, `docs/getting-started/quickstart.md` → `docs/getting-started/quickstart.en.md`, `docs/user-guide/avro-serializer.md` → `docs/user-guide/avro-serializer.en.md`, `docs/changelog.md` → `docs/changelog.en.md`
- [x] T003 [P] Create directory scaffolds for new content sections: `docs/concepts/`, `docs/how-to/`, `docs/migration/`
- [x] T004 Update `mkdocs.yml` with: i18n plugin (suffix mode, en + fr), multilingual search (en + fr separator), Material feature flags (`navigation.tabs`, `navigation.sections`, `navigation.instant`, `navigation.top`, `navigation.indexes`, `navigation.footer`, `content.code.copy`, `content.tabs.link`, `search.highlight`, `search.suggest`, `toc.integrate`), language switcher (`extra.alternate`), and expanded nav (concepts, how-to, migration sections) — depends on T002, T003
- [x] T005 Verify baseline build passes `uv run --group docs mkdocs build --strict` — depends on T001, T004

**Checkpoint**: Infrastructure ready — all content tasks can now begin in parallel.

---

## Phase 2: US1 — New Visitor Understands the Problem and Gets Started (Priority: P1) MVP

**Goal**: Homepage communicates the value proposition clearly; quickstart guides new users to a working serialization example.

**Independent Test**: A developer unfamiliar with the library follows only the homepage and quickstart and produces valid Confluent-framed Avro bytes.

- [x] T006 [P] [US1] Rewrite `docs/index.en.md` — homepage with: problem statement (what apicurio-serdes solves), target audience (Python data engineers), value proposition vs confluent-kafka, feature overview, and link to quickstart — to pass [TS-001] — depends on T002
- [x] T007 [P] [US1] Enhance `docs/getting-started/quickstart.en.md` — add full working serialization example (prerequisites, install, registry setup or local alternative, minimal producer script) and troubleshooting section covering: wrong registry URL, non-existent artifact, invalid input data — to pass [TS-002, TS-003] — depends on T002

**Checkpoint**: US1 complete — first-time visitor can get from zero to working serialization in a single reading.

---

## Phase 3: US2 — Confluent-kafka Migrant Identifies All Differences (Priority: P2)

**Goal**: Migration guide gives existing confluent-kafka users a complete map of API and behavioral differences.

**Independent Test**: A developer familiar with confluent-kafka reads only the migration guide and adapts a sample producer.

- [x] T008 [US2] Write `docs/migration/from-confluent-kafka.en.md` — side-by-side API comparison table (class names, constructor parameters, invocation patterns), group_id explanation (what it is, why required, mapping from Confluent schema naming), behavioral differences table, and minimal migration code example showing import-and-config-only change — to pass [TS-004, TS-005, TS-006] — depends on T003

**Checkpoint**: US2 complete — a confluent-kafka user can identify all differences and migrate their producer code.

---

## Phase 4: US3 — Developer Finds Exact API Details (Priority: P3)

**Goal**: API reference auto-generated from docstrings covers every public symbol with zero missing-documentation warnings.

**Independent Test**: Every public symbol appears in the reference with description, parameters, return type, exceptions, and a usage example.

- [x] T009 [US3] Audit and complete Google-style docstrings for all public symbols in `src/apicurio_serdes/` — cover: AvroSerializer (constructor signature with all parameters and defaults, description, usage example), all public exceptions (SchemaNotFoundError including group_id and artifact_id attributes, RegistryConnectionError, SerializationError with trigger conditions), all public methods (parameters, return type, raised exceptions) — to pass [TS-007, TS-009]
- [x] T010 [US3] Update `docs/api-reference/index.md` to reference all public symbols via `:::` directives; run `uv run --group docs mkdocs build --strict` and confirm zero missing-documentation warnings — to pass [TS-008] — depends on T009

**Checkpoint**: US3 complete — API reference covers 100% of public symbols with zero build warnings.

---

## Phase 5: US5 — Conceptual Pages + How-to Guides (Priority: P5)

**Goal**: Dedicated explanation pages for wire format, schema caching, and addressing model; task-oriented how-to guides for custom serialization, identifier selection, and error handling.

**Independent Test**: A developer with no prior Apicurio knowledge reads the conceptual pages and correctly answers: what is the magic byte for, when does the cache expire, and how does group_id differ from Confluent's model.

### Conceptual Pages (US5)

- [x] T011 [P] [US5] Write `docs/concepts/wire-format.en.md` — byte-level layout diagram (magic byte `0x00`, 4-byte schema identifier, Avro binary payload), purpose of each field, difference between globalId and contentId, when each identifier is used — to pass [TS-014] — depends on T003
- [x] T012 [P] [US5] Write `docs/concepts/schema-caching.en.md` — how the cache is populated on first use, cache lifetime (per-client-instance), when to create a new instance, thread-safety guarantees — to pass [TS-015] — depends on T003
- [x] T013 [P] [US5] Write `docs/concepts/addressing-model.en.md` — group → artifact → version hierarchy diagram, why group_id is mandatory in apicurio-serdes, mapping table from Confluent subject naming to Apicurio group/artifact model — to pass [TS-016] — depends on T003

### How-to Guides (Cross-cutting, FR-007)

- [x] T014 [P] Write `docs/how-to/custom-serialization.en.md` — to_dict hook pattern with dataclass example and Pydantic example, when to use it, limitations — depends on T003
- [x] T015 [P] Write `docs/how-to/identifier-selection.en.md` — globalId vs contentId decision guide: tradeoffs, registry behaviour, when to use each — depends on T003
- [x] T016 [P] Write `docs/how-to/error-handling.en.md` — handling SchemaNotFoundError (group_id, artifact_id attributes), RegistryConnectionError (retry pattern), SerializationError (input validation pattern) with code examples — depends on T003

**Checkpoint**: US5 complete — conceptual pages and how-to guides answer "why" and "how" questions beyond the quickstart.

---

## Phase 6: US4 — French-speaking Developer Reads Complete Documentation in French (Priority: P4)

**Goal**: Every narrative section available in English is also available in French with equivalent depth.

**Independent Test**: A French speaker follows the French documentation from start to finish and performs all quickstart tasks without switching to English.

**CRITICAL**: This phase depends on ALL English content tasks (T006–T016) being complete. All translation tasks within this phase can run in parallel.

- [x] T017 [P] [US4] Translate `docs/index.fr.md` — French homepage matching index.en.md structure and depth — to pass [TS-010, TS-011] — depends on T006
- [x] T018 [P] [US4] Translate `docs/getting-started/installation.fr.md` — French installation guide — to pass [TS-011] — depends on T002
- [x] T019 [P] [US4] Translate `docs/getting-started/quickstart.fr.md` — French quickstart including troubleshooting section, fully functional end-to-end in French — to pass [TS-011, TS-012] — depends on T007
- [x] T020 [P] [US4] Translate `docs/user-guide/avro-serializer.fr.md` — French user guide — to pass [TS-011] — depends on T002
- [x] T021 [P] [US4] Translate `docs/concepts/wire-format.fr.md` — French wire format conceptual page — to pass [TS-011] — depends on T011
- [x] T022 [P] [US4] Translate `docs/concepts/schema-caching.fr.md` — French schema caching conceptual page — to pass [TS-011] — depends on T012
- [x] T023 [P] [US4] Translate `docs/concepts/addressing-model.fr.md` — French addressing model conceptual page — to pass [TS-011] — depends on T013
- [x] T024 [P] [US4] Translate `docs/how-to/custom-serialization.fr.md` — French custom serialization guide — to pass [TS-011] — depends on T014
- [x] T025 [P] [US4] Translate `docs/how-to/identifier-selection.fr.md` — French identifier selection guide — to pass [TS-011] — depends on T015
- [x] T026 [P] [US4] Translate `docs/how-to/error-handling.fr.md` — French error handling guide — to pass [TS-011] — depends on T016
- [x] T027 [P] [US4] Translate `docs/migration/from-confluent-kafka.fr.md` — French migration guide — to pass [TS-011] — depends on T008
- [x] T028 [P] [US4] Translate `docs/changelog.fr.md` — French changelog — to pass [TS-011] — depends on T002

**Checkpoint**: US4 complete — French and English page trees are structurally identical with full content parity.

---

## Final Phase: Validation & Polish

**Purpose**: End-to-end build validation, content quality gate, and acceptance criteria verification.

- [x] T029 Run `uv run --group docs mkdocs build --strict` — verify zero build warnings and zero missing-documentation warnings across the complete site (EN + FR) — to pass [TS-008] — depends on T017–T028
- [x] T030 Verify EN/FR page tree parity — every page in the English site has a corresponding French page; use `find docs/ -name "*.en.md"` vs `find docs/ -name "*.fr.md"` to confirm 1:1 mapping (excluding api-reference/index.md) — to pass [TS-011] — depends on T017–T028
- [x] T031 Verify full-text search returns relevant results — spot-check search for: "serializer", "group_id", "wire format", "caching", "migration", "error" in both English and French by inspecting the generated search index in `site/search/search_index.json` — to pass [TS-013] — depends on T029
- [x] T032 Validate all code examples — review all `.en.md` files with code blocks and confirm every Python snippet is syntactically valid and consistent with the current public API; fix any stale examples — depends on T029

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Infrastructure)**: T001, T002, T003 are parallel; T004 depends on T002 + T003; T005 depends on T001 + T004
- **Phases 2–5 (English Content)**: All unblock after T005; T006–T016 can run in parallel with each other (different files)
- **Phase 4 (US3 sequential)**: T010 depends on T009 (docstrings before API ref update)
- **Phase 6 (French Translations)**: Each translation task depends on its English counterpart; all T017–T028 can run in parallel
- **Final Phase**: T029 depends on all T017–T028; T030–T032 depend on T029

### Critical Path

`T001 → T004 → T005 → T009 → T010 → T017–T028 (parallel batch) → T029 → T030 → T031 → T032`

### Parallel Batches

**Batch A** (Phase 1): T001, T002, T003 (then T004 → T005)

**Batch B** (Phases 2–5, after T005): T006, T007, T008, T009, T011, T012, T013, T014, T015, T016

**Batch C** (Phase 6, after Batch B): T017, T018, T019, T020, T021, T022, T023, T024, T025, T026, T027, T028

**Batch D** (Validation, after Batch C): T029 → T030, T031, T032

### MVP Scope

Complete Phase 1 + Phase 2 (T001–T007): functional site scaffold with i18n enabled, homepage communicating problem clearly, and quickstart guiding new users to a working example (US1, P1).

---

## Notes

- [P] tasks = different files, no shared dependencies — safe to run concurrently
- French translations (Phase 6) are the most parallelizable batch in the feature — assign all 12 in one session
- `mkdocs-static-i18n` with suffix mode expects nav paths WITHOUT language suffix (e.g., `index.md`, not `index.en.md`) — the plugin resolves to `.en.md` or `.fr.md` based on build language
- API reference (`docs/api-reference/index.md`) has no language suffix and is shared across both language builds
- The `uv run --group docs mkdocs build --strict` command is the quality gate — run it after every phase
