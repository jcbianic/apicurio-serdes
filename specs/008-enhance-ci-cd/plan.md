# Implementation Plan: Enhance CI/CD Pipeline

**Branch**: `008-enhance-ci-cd` | **Date**: 2026-03-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/008-enhance-ci-cd/spec.md`

## Summary

Establish a complete CI/CD pipeline for the apicurio-serdes project: align local
pre-commit linting with CI, add quality gates as required status checks, publish
pre-release packages to TestPyPI on PRs, configure ReadTheDocs for automatic
documentation builds, implement draft-PR conditional CI, and document the setup.

## Technical Context

**Language/Version**: Python 3.10 (minimum supported; `requires-python = ">=3.10"`)
**Primary Dependencies**: ruff 0.15.5, mypy 1.19.1, pre-commit, GitHub Actions
**Storage**: N/A (configuration-only feature)
**Testing**: pytest 8.x with pytest-cov (100% branch coverage enforced)
**Target Platform**: GitHub Actions (ubuntu-latest), ReadTheDocs
**Project Type**: Single Python package (hatchling build backend)
**Performance Goals**: CI completes in under 5 minutes for non-draft PRs
**Constraints**: Single required secret (`TESTPYPI_API_TOKEN`); all other config derived from repo files
**Scale/Scope**: Single repository, single Python version in CI (3.10)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. API Compatibility | N/A | CI/CD does not affect public API |
| II. No Schema Opinion | N/A | CI/CD does not affect schema handling |
| III. Test-First (NON-NEGOTIABLE) | COMPLIANT | CI enforces 100% coverage. YAML config files are declarative, not production code — validated through integration rather than unit tests. Any Python helper scripts must follow TDD. |
| IV. Wire Format Fidelity | N/A | CI/CD does not affect wire formats |
| V. Simplicity | COMPLIANT | Minimal workflow design; single secret; standard tooling |
| Quality Standards (coverage) | COMPLIANT | CI enforces `--cov-fail-under=100 --cov-branch` |
| Quality Standards (docs) | COMPLIANT | RTD auto-publishes docs; mkdocs build validated in CI |
| Development Workflow ([DOCS] task) | COMPLIANT | tasks.md will include [DOCS] task for CI/CD setup guide |
| Development Workflow (TDD) | COMPLIANT | Per constitution: TDD mandatory. `/iikit-04-testify` will run before `/iikit-05-tasks` |

**TDD applicability note**: This feature creates CI/CD configuration (YAML workflow files,
`.pre-commit-config.yaml`, `.readthedocs.yaml`, `mkdocs.yml`). These are declarative
configuration files, not executable production code. They cannot be unit-tested in the
Red-Green-Refactor sense. Validation occurs through integration: pushing a branch and
verifying workflows execute correctly. Per Constitution Principle III, any Python scripts
or helpers created as part of this feature must follow strict TDD.

## Architecture

```
Developer Workstation          GitHub Actions CI               External Services
┌──────────────────┐     ┌────────────────────────────┐     ┌──────────────┐
│ pre-commit        │push │ ci.yml                      │     │ TestPyPI     │
│ ├─ ruff check    ├────▶│ ├─ lint (pre-commit)  [ALL] │────▶│ (pre-release │
│ └─ ruff format   │     │ ├─ typecheck (mypy)  [!DFT] │     │  packages)   │
└──────────────────┘     │ ├─ test (pytest+cov) [!DFT] │     └──────────────┘
                         │ ├─ docs-build        [!DFT] │
                         │ └─ publish-testpypi  [!DFT] │     ┌──────────────┐
                         │    (needs: lint+type+test)   │     │ ReadTheDocs  │
                         └────────────────────────────┘     │ (webhook     │
                                                       ◀───▶│  auto-build) │
                         ┌────────────────────────────┐     └──────────────┘
                         │ Branch Protection            │
                         │ Required: lint, typecheck,   │
                         │   test, docs-build           │
                         └────────────────────────────┘

[ALL] = runs on all PRs including drafts
[!DFT] = skipped on draft PRs
```

### Key Design Decisions

1. **Single source of truth for linting** (D1): CI runs `pre-commit run --all-files`
   using the same `.pre-commit-config.yaml` as local development. Alignment is
   guaranteed by design — there is only one configuration source.

2. **TestPyPI via API token** (D3): `pypa/gh-action-pypi-publish` with
   `TESTPYPI_API_TOKEN` secret. Trusted Publishers (OIDC) recommended as future
   enhancement.

3. **ReadTheDocs via webhook** (D5): Native GitHub integration with PR preview
   builds. No GitHub secret needed. CI also validates docs build for faster feedback.

4. **Conditional CI on draft PRs** (D6): Only lint runs on drafts. Full suite
   triggers on `ready_for_review` event.

5. **Version management** (D4): `{base_version}rc{github.run_number}` — globally
   unique, PEP 440 compliant, no conflicts across parallel PRs.

See [research.md](research.md) for full decision log with alternatives considered.

## Project Structure

### Documentation (this feature)

```text
specs/008-enhance-ci-cd/
  spec.md              # Feature specification
  plan.md              # This file
  research.md          # Technology decisions
  data-model.md        # Configuration entity model
  quickstart.md        # Setup guide with test scenarios
  contracts/           # Workflow interface contracts
    ci-cd-interfaces.md
  tasks.md             # Task breakdown (created by /iikit-tasks)
```

### Source Code (repository root)

```text
.pre-commit-config.yaml          # NEW: ruff hooks, pinned to v0.15.5
.readthedocs.yaml                # NEW: RTD build configuration
mkdocs.yml                       # NEW: documentation site config

.github/
  workflows/
    ci.yml                       # NEW: main CI workflow (5 jobs)

docs/
  index.md                       # NEW: documentation home page (minimal)
  user-guide/                    # EXISTING
    async-client.md
    deserialization.md
    deserializer.md
  setup/
    ci-cd-secrets.md             # NEW: CI/CD setup documentation (FR-015)
```

**Structure Decision**: No new Python source files. This feature adds CI/CD
configuration files at the repository root and in `.github/workflows/`. Documentation
scaffolding is minimal — just enough for `mkdocs build` to succeed. The existing
`docs/user-guide/` structure is preserved unchanged.

## Files to Create

| File | Purpose | FR Coverage |
|---|---|---|
| `.pre-commit-config.yaml` | Ruff lint + format hooks, pinned version | FR-001, FR-002, FR-003 |
| `.github/workflows/ci.yml` | CI workflow with 5 jobs | FR-003, FR-004, FR-005, FR-010, FR-012, FR-013 |
| `.readthedocs.yaml` | RTD build configuration | FR-006, FR-007, FR-008 |
| `mkdocs.yml` | MkDocs site configuration | FR-006, FR-007 |
| `docs/index.md` | Documentation home page | FR-006 (build prerequisite) |
| `docs/setup/ci-cd-secrets.md` | CI/CD setup documentation | FR-015 |

## Configuration to Apply (Manual)

| Setting | Where | FR Coverage |
|---|---|---|
| Add `TESTPYPI_API_TOKEN` secret | GitHub repo settings | FR-005, FR-009 |
| Enable PR builds | ReadTheDocs dashboard | FR-006 |
| Connect repository | ReadTheDocs dashboard | FR-007, FR-008 |
| Add required status checks | GitHub branch protection | FR-010, FR-014 |
| Set branch protection rules | GitHub repo settings | FR-014 |

## Requirements Traceability

| Requirement | Addressed By |
|---|---|
| FR-001 | `.pre-commit-config.yaml` (ruff hooks with pyproject.toml rules) |
| FR-002 | `.pre-commit-config.yaml` (version pinned to v0.15.5) |
| FR-003 | `ci.yml` lint job (runs pre-commit, same config as local) |
| FR-004 | `ci.yml` publish-testpypi job (version: X.Y.ZrcN) |
| FR-005 | `ci.yml` publish-testpypi job (uses TESTPYPI_API_TOKEN) |
| FR-006 | `.readthedocs.yaml` + RTD dashboard PR build setting |
| FR-007 | `.readthedocs.yaml` + RTD dashboard (auto-build on tag/main) |
| FR-008 | ReadTheDocs webhook-based authentication |
| FR-009 | Single secret: TESTPYPI_API_TOKEN (all else from repo files) |
| FR-010 | `ci.yml` jobs as required status checks + branch protection |
| FR-011 | `docs/setup/ci-cd-secrets.md` (guide to create PRs as draft) |
| FR-012 | `ci.yml` draft condition skips heavy jobs |
| FR-013 | `ci.yml` ready_for_review trigger runs full suite |
| FR-014 | Branch protection rules (manual configuration, documented) |
| FR-015 | `docs/setup/ci-cd-secrets.md` (secret names, sources, steps) |

## Complexity Tracking

No constitution violations requiring justification. All design decisions
align with constitutional principles.

## Implementation Strategy

### Phase 1: Pre-commit + CI Linting (US1)
Create `.pre-commit-config.yaml` and `.github/workflows/ci.yml` with lint job.
Verify local and CI linting produce identical results.

### Phase 2: Full CI Quality Gates (US5)
Add typecheck, test, and docs-build jobs to CI workflow.
Create `mkdocs.yml` and `docs/index.md` for docs-build validation.

### Phase 3: Draft PR Handling (US6)
Add conditional execution to CI jobs based on draft status.
Test with draft and non-draft PRs.

### Phase 4: TestPyPI Publishing (US2)
Add publish-testpypi job with version override and secret.
Verify package installs from TestPyPI.

### Phase 5: ReadTheDocs Integration (US3)
Create `.readthedocs.yaml`. Configure RTD dashboard.
Verify PR preview builds and release builds.

### Phase 6: Secrets & Documentation (US4, US7)
Create setup documentation. Configure branch protection.
Verify end-to-end pipeline with all quality gates.
