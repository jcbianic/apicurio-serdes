# Tasks: CI/CD Pipeline

**Input**: Design documents from `specs/005-ci-cd-pipeline/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**TDD**: MANDATORY per CONSTITUTION.md Principle III. Test tasks precede implementation tasks in every phase.

**Note on shared deliverable**: `ci.yml` covers US1 (quality gate), US5 (docs build), and US6 (multi-platform).
Test tasks for all three user stories are grouped in Phase 3 to maintain TDD discipline on the shared file.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared state)
- **[Story]**: User story this task belongs to (US1–US6)
- **[DOCS]**: Documentation task mandated by CONSTITUTION.md §Development Workflow

---

## Phase 1: Setup

**Purpose**: Directory structure and dev-tooling prerequisites

- [ ] T001 [P] Create .github/workflows/ directory structure (prerequisite for all workflow files)
- [ ] T002 [P] Add pip-audit to dev dependency group in pyproject.toml (required by security.yml)

---

## Phase 3: US1 — Automated Quality Gate (P1) MVP

**Goal**: Every push and PR automatically runs lint, typecheck, tests with coverage enforcement, docs build, and multi-platform matrix

**Independent Test**: Open a PR with a passing change — verify all ci.yml jobs complete; open a PR with a failing test — verify pipeline blocks merge

> **TDD — write tests first, confirm they FAIL before creating ci.yml**

> Note: US5 (Documentation Build Validation, P2) and US6 (Multi-Platform Compatibility, P3) are also
> implemented in ci.yml. Their test tasks are included here to maintain TDD discipline on the shared file.

### Tests for US1 + US5 + US6

- [ ] T003 [P] [US1] Write YAML validation tests for ci.yml triggers, lint job, typecheck job, and test job structure in tests/ci/test_ci_workflow.py [TS-001, TS-002, TS-003, TS-004, TS-005] (depends on T001)
- [ ] T004 [P] [US1] Write YAML validation tests for ci.yml coverage artifact upload configuration in tests/ci/test_ci_artifacts.py [TS-006] (depends on T001)
- [ ] T005 [P] [US5] Write YAML validation tests for ci.yml docs job using `uv run mkdocs build --strict` in tests/ci/test_docs_job.py [TS-023, TS-024] (depends on T001)
- [ ] T006 [P] [US6] Write YAML validation tests for ci.yml test matrix covering Python 3.10, 3.11, 3.12, 3.13 in tests/ci/test_matrix.py [TS-025, TS-026] (depends on T001)

### Implementation for US1

- [ ] T007 [US1] Create .github/workflows/ci.yml with lint, typecheck, test (3.10–3.13 matrix), and docs jobs per specs/005-ci-cd-pipeline/contracts/ci-workflow.md [TS-001, TS-002, TS-003, TS-004, TS-005, TS-006, TS-023, TS-024, TS-025, TS-026] (depends on T003, T004, T005, T006)

**Checkpoint**: All ci.yml YAML tests pass; four jobs (lint, typecheck, test, docs) confirmed; test matrix covers all four Python versions

---

## Phase 4: US2 — Open-Source Quality Signaling (P1)

**Goal**: Coverage results uploaded to Codecov; CI status and coverage percentage badges visible in README

**Independent Test**: Verify a successful CI run uploads coverage to Codecov and the badge reflects the current coverage percentage

> **TDD — write tests first, confirm they FAIL before updating ci.yml and README**

### Tests for US2

- [ ] T008 [P] [US2] Write YAML validation tests for ci.yml upload-artifact and codecov/codecov-action@v5 steps in tests/ci/test_codecov_integration.py [TS-007, TS-008, TS-010] (depends on T001)
- [ ] T009 [P] [US2] Write README badge presence tests in tests/ci/test_readme_badges.py asserting CI status and Codecov badge markdown is present [TS-009]

### Implementation for US2

- [ ] T010 [US2] Update .github/workflows/ci.yml test job to add upload-artifact (coverage XML) and codecov/codecov-action@v5 steps [TS-007, TS-008, TS-010] (depends on T007, T008)
- [ ] T011 [P] [US2] Add GitHub Actions CI status badge and Codecov coverage percentage badge to README.md [TS-009] (depends on T009)

**Checkpoint**: CI run uploads coverage to Codecov; both badges render correctly in README

---

## Phase 5: US3 — Automated Package Publication (P1)

**Goal**: GitHub Release event triggers sequential staging-to-production publish pipeline with OIDC trusted publishing and version validation

**Independent Test**: Create a release — verify package appears on TestPyPI; confirm it is promoted to PyPI; trigger with mismatched version and confirm pipeline fails before any publication

> **TDD — write tests first, confirm they FAIL before creating publish.yml**

### Tests for US3

- [ ] T012 [US3] Write YAML validation tests for publish.yml trigger (release: published), sequential job chain (validate-version → build → publish-testpypi → validate-testpypi → publish-pypi), OIDC permissions, and version check step in tests/ci/test_publish_workflow.py [TS-011, TS-012, TS-013, TS-014, TS-015, TS-016, TS-017] (depends on T001)

### Implementation for US3

- [ ] T013 [US3] Create .github/workflows/publish.yml with validate-version, build, publish-testpypi, validate-testpypi, and publish-pypi jobs using pypa/gh-action-pypi-publish@v1 with OIDC trusted publishing per specs/005-ci-cd-pipeline/contracts/publish-workflow.md [TS-011, TS-012, TS-013, TS-014, TS-015, TS-016, TS-017] (depends on T012)

**Checkpoint**: publish.yml sequential job chain passes YAML validation; version mismatch check and OIDC configuration confirmed

---

## Phase 6: US4 — Automated Security Audit (P2)

**Goal**: Dependency vulnerability scanning on every PR and on weekly schedule; CodeQL static security analysis; Dependabot automated dependency update PRs

**Independent Test**: Introduce a dependency with a known vulnerability — verify pipeline reports it; check weekly schedule trigger is present

> **TDD — write tests first, confirm they FAIL before creating security.yml and dependabot.yml**

### Tests for US4

- [ ] T014 [P] [US4] Write YAML validation tests for security.yml triggers (pull_request targeting main, weekly cron Monday 06:00 UTC), dependency-audit job (pip-audit), and codeql job in tests/ci/test_security_workflow.py [TS-018, TS-019, TS-020, TS-021, TS-022] (depends on T001)
- [ ] T015 [P] [US4] Write YAML validation tests for dependabot.yml pip package-ecosystem (daily) and github-actions package-ecosystem (weekly) configuration in tests/ci/test_dependabot.py [TS-019]

### Implementation for US4

- [ ] T016 [US4] Create .github/workflows/security.yml with dependency-audit (pip-audit) and codeql jobs per specs/005-ci-cd-pipeline/contracts/security-workflow.md [TS-018, TS-019, TS-020, TS-021, TS-022] (depends on T002, T014)
- [ ] T017 [P] [US4] Create .github/dependabot.yml with daily pip package-ecosystem and weekly github-actions package-ecosystem schedules [TS-019] (depends on T015)

**Checkpoint**: security.yml triggers on PRs and weekly schedule; dependabot.yml auto-PR configuration confirmed by YAML tests

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, setup guide validation, and compliance

- [ ] T018 [P] [DOCS] Create docs/user-guide/ci-cd.md documenting pipeline architecture, badge setup, Codecov app installation, TestPyPI and PyPI trusted publisher registration, and release process
- [ ] T019 [P] Run specs/005-ci-cd-pipeline/quickstart.md validation scenarios: verify trusted publisher setup steps, badge URL correctness, and first-release checklist accuracy

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 3 (US1)**: T003–T006 depend on T001; T007 depends on T003, T004, T005, T006
- **Phase 4 (US2)**: T010 depends on T007 (ci.yml must exist); T011 depends on T009
- **Phase 5 (US3)**: T012 depends on T001; T013 depends on T012
- **Phase 6 (US4)**: T016 depends on T002 and T014; T017 depends on T015
- **Final Phase**: Depends on all implementation tasks complete

### Parallel Opportunities

| Batch | Tasks | Condition |
|-------|-------|-----------|
| 1 | T001, T002 | Immediately — no dependencies |
| 2 | T003, T004, T005, T006 | After T001 |
| 3 | T007 | After T003, T004, T005, T006 |
| 4 | T008, T009, T012, T014, T015 | After T001 (test-only batch, safe to parallelize) |
| 5 | T010, T011, T013, T016, T017 | After respective tests and T007 (where needed) |
| 6 | T018, T019 | After all implementation complete |

### Critical Path

`T001 → T003/T004/T005/T006 → T007 → T010 → Final`

### Story Independence

- US1, US5, US6 share ci.yml — cannot be independently deployed but are independently testable via YAML validation
- US2 builds directly on US1 (Codecov action added to ci.yml test job)
- US3 (publish.yml) is fully independent of US1/US2
- US4 (security.yml + dependabot.yml) is fully independent; pip-audit dependency (T002) is its only setup prerequisite

---

## Notes

- [P] = different files, no shared state — run concurrently
- [DOCS] task mandated by CONSTITUTION.md §Development Workflow ("every feature's tasks.md must include at least one [DOCS] task")
- TDD is MANDATORY per CONSTITUTION.md Principle III — no workflow YAML without a prior failing test
- Coverage threshold for the test suite: 100% line and branch (CONSTITUTION.md Quality Standards)
- Trusted publishing for TestPyPI and PyPI requires one-time manual registration (documented in quickstart.md)
- Codecov requires installing the GitHub App on the repository (documented in quickstart.md)
