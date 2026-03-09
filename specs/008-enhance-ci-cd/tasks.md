# Tasks: Enhance CI/CD Pipeline

**Input**: Design documents from `specs/008-enhance-ci-cd/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ci-cd-interfaces.md

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[USn]**: Which user story this task belongs to
- **[DOCS]**: Documentation task (per constitution)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create directory structure and foundational config that all stories depend on

- [x] T001 Create `.github/workflows/` directory structure
- [x] T002 [P] Create `mkdocs.yml` with material theme, mkdocstrings plugin, and nav referencing existing `docs/user-guide/` pages
- [x] T003 [P] Create `docs/index.md` as minimal documentation home page (required for mkdocs build to succeed)

**Checkpoint**: Directory structure and docs scaffolding ready

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: CI workflow skeleton and pre-commit config that MUST be in place before story-specific work

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Create `.pre-commit-config.yaml` with ruff-pre-commit pinned to v0.15.5, hooks: ruff (lint with --fix) and ruff-format [TS-001, TS-004, TS-005]
- [x] T005 Create `.github/workflows/ci.yml` with workflow triggers (pull_request: opened, synchronize, reopened, ready_for_review; push: main) and lint job using pre-commit/action@v3.0.1 [TS-002, TS-003]
- [x] T006 Verify pre-commit runs locally with `pre-commit run --all-files` and produces identical results to CI lint job [TS-001, TS-002, TS-003]

**Checkpoint**: Pre-commit + CI lint alignment verified (US1 complete). All subsequent phases can begin.

---

## Phase 3: User Story 1 — Align Linting Between Pre-Commit and CI (Priority: P1) MVP

**Goal**: Identical ruff enforcement locally and in CI
**Independent Test**: Push code with ruff violations, verify pre-commit catches them, verify CI passes when pre-commit passes

> Note: US1 is fully delivered by Phase 2 tasks (T004, T005, T006). This phase exists as a verification checkpoint.

**Checkpoint**: US1 complete — linting alignment verified [TS-001, TS-002, TS-003, TS-004, TS-005]

---

## Phase 4: User Story 5 — Quality Gates as Required Status Checks (Priority: P2)

**Goal**: CI enforces tests, coverage, type checking, and docs build as merge-blocking status checks
**Independent Test**: Open a PR with a test failure, verify merge is blocked

- [x] T007 [US5] Add `typecheck` job to `.github/workflows/ci.yml`: setup-uv, `uv sync --group dev`, `uv run mypy`; condition: non-draft or push [TS-025]
- [x] T008 [US5] Add `test` job to `.github/workflows/ci.yml`: setup-uv, `uv sync --group dev`, `uv run pytest`; condition: non-draft or push [TS-025]
- [x] T009 [US5] Add `docs-build` job to `.github/workflows/ci.yml`: setup-uv, `uv sync --group docs`, `uv run mkdocs build --strict`; condition: non-draft or push [TS-016, TS-025]
- [x] T010 [US5] Document branch protection configuration (required status checks: lint, typecheck, test, docs-build) in `docs/setup/ci-cd-secrets.md` [TS-022, TS-023, TS-024, TS-026]

**Checkpoint**: US5 complete — all four quality gate jobs defined in CI [TS-022, TS-023, TS-024, TS-025, TS-026]

---

## Phase 5: User Story 6 — Draft PR with Conditional CI Triggering (Priority: P2)

**Goal**: Draft PRs run only lint; full suite runs on ready_for_review
**Independent Test**: Open draft PR, verify only lint runs; mark ready, verify full suite triggers

- [x] T011 [US6] Add draft-skip condition (`github.event.pull_request.draft == false || github.event_name == 'push'`) to typecheck, test, docs-build jobs in `.github/workflows/ci.yml` [TS-028, TS-029, TS-030, TS-031, TS-032]
- [x] T012 [US6] Verify `ready_for_review` is included in pull_request event types in `.github/workflows/ci.yml` [TS-031]

**Checkpoint**: US6 complete — conditional CI execution verified [TS-027, TS-028, TS-029, TS-030, TS-031, TS-032]

---

## Phase 6: User Story 2 — Publish Package to TestPyPI (Priority: P1)

**Goal**: Every non-draft PR automatically publishes a pre-release to TestPyPI
**Independent Test**: Open PR, verify TestPyPI package with rcN version is published and installable

- [x] T013 [US2] Add `publish-testpypi` job to `.github/workflows/ci.yml`: needs [lint, typecheck, test], condition: PR + non-draft, version override via sed to `X.Y.ZrcN`, `uv build`, pypa/gh-action-pypi-publish@release/v1 with TESTPYPI_API_TOKEN [TS-006, TS-008, TS-009, TS-010, TS-011]
- [x] T014 [US2] Verify published package version follows PEP 440 `X.Y.ZrcN` format using github.run_number [TS-009, TS-011]

**Checkpoint**: US2 complete — TestPyPI publishing verified [TS-006, TS-007, TS-008, TS-009, TS-010, TS-011]

---

## Phase 7: User Story 3 — Publish Documentation to ReadTheDocs (Priority: P1)

**Goal**: Docs auto-build on PR (preview link) and on release (primary site)
**Independent Test**: Open PR, verify RTD preview link appears as status check

- [x] T015 [US3] Create `.readthedocs.yaml` with version 2, build OS ubuntu-24.04, Python 3.10, mkdocs configuration reference, uv-based build commands [TS-012, TS-015]
- [x] T016 [US3] Document ReadTheDocs dashboard configuration steps (connect repo, enable PR builds) in `docs/setup/ci-cd-secrets.md` [TS-013, TS-014, TS-015]

**Checkpoint**: US3 complete — ReadTheDocs integration configured [TS-012, TS-013, TS-014, TS-015, TS-016]

---

## Phase 8: User Story 4 — Simplify Secrets Configuration (Priority: P1)

**Goal**: Only TESTPYPI_API_TOKEN required; no hardcoded config in workflows
**Independent Test**: Verify workflow uses only `${{ secrets.TESTPYPI_API_TOKEN }}`; no other hardcoded values

- [x] T017 [US4] Audit `.github/workflows/ci.yml` to ensure no hardcoded configuration values; only `${{ secrets.TESTPYPI_API_TOKEN }}` as secret reference [TS-017, TS-020, TS-021]
- [x] T018 [US4] Add error handling for missing TESTPYPI_API_TOKEN in publish-testpypi job with clear error message [TS-018, TS-019]

**Checkpoint**: US4 complete — minimal secrets configuration verified [TS-017, TS-018, TS-019, TS-020, TS-021]

---

## Phase 9: User Story 7 — Document API Key Setup Instructions (Priority: P3)

**Goal**: Clear documentation for configuring GitHub secrets and CI/CD pipeline
**Independent Test**: Follow docs to configure secrets on a test repo; all CI workflows pass

- [x] T019 [DOCS] [US7] Create `docs/setup/ci-cd-secrets.md` with: required secrets table (name, source, scope), step-by-step instructions for obtaining TESTPYPI_API_TOKEN, ReadTheDocs connection steps, branch protection configuration, troubleshooting guide for missing/expired secrets [TS-033, TS-034, TS-035, TS-036, TS-037]
- [x] T020 [DOCS] [US7] Add draft PR creation guidance to `docs/setup/ci-cd-secrets.md` explaining how to create PRs as draft and the CI behavior difference [TS-027]

**Checkpoint**: US7 complete — setup documentation verified [TS-033, TS-034, TS-035, TS-036, TS-037]

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cleanup

- [x] T021 Run `pre-commit run --all-files` to verify all existing code passes linting
- [x] T022 Run `uv run mkdocs build --strict` to verify documentation builds without warnings
- [x] T023 Verify all CI workflow YAML syntax with `actionlint` or manual review
- [x] T024 Run quickstart.md end-to-end validation checklist

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup ─────────────────────────────────┐
                                                 ▼
Phase 2: Foundational (pre-commit + CI lint) ───┐
                                                 │
  ┌──────────────────────────────────────────────┤
  │                                              │
  ▼                                              ▼
Phase 3: US1 (verification only)    Phase 4: US5 (quality gates)
                                                 │
                                                 ▼
                                    Phase 5: US6 (draft PR handling)
                                                 │
                                    ┌────────────┤
                                    ▼            ▼
                          Phase 6: US2    Phase 7: US3
                          (TestPyPI)      (ReadTheDocs)
                                    │            │
                                    └──────┬─────┘
                                           ▼
                                    Phase 8: US4 (secrets audit)
                                           │
                                           ▼
                                    Phase 9: US7 (documentation)
                                           │
                                           ▼
                                    Phase 10: Polish
```

### Parallel Opportunities

- **Phase 1**: T002 and T003 can run in parallel (different files)
- **Phase 4**: T007, T008, T009 can be implemented simultaneously (separate jobs in same workflow file, but sequential edits recommended)
- **Phase 6 + Phase 7**: US2 (TestPyPI) and US3 (ReadTheDocs) can run in parallel after Phase 5 completes (different files, no dependencies)
- **Phase 10**: T021, T022, T023 can run in parallel (independent validations)

### Critical Path

T001 → T004 → T005 → T006 → T007/T008/T009 → T011 → T013 → T017 → T019 → T024

Longest chain: 10 tasks (Setup → Foundation → Quality Gates → Draft handling → TestPyPI → Secrets audit → Docs → Polish)

---

## Notes

- [P] tasks = different files, no dependencies
- [USn] label maps task to specific user story for traceability
- [DOCS] marks documentation tasks (per constitution requirement)
- This feature is configuration-only (YAML, Markdown) — no Python production code
- Per constitution TDD note: YAML config files are validated through integration, not unit tests
- Manual GitHub settings (secrets, branch protection, RTD dashboard) are documented but not automated
- Total tasks: 24 | Per-story: US1=3(shared), US2=2, US3=2, US4=2, US5=4, US6=2, US7=2 | Setup=3, Polish=4
