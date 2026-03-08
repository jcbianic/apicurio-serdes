# Implementation Plan: CI/CD Pipeline

**Branch**: `005-ci-cd-pipeline` | **Date**: 2026-03-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/005-ci-cd-pipeline/spec.md`

## Summary

Implement a production-grade CI/CD pipeline for an open-source Python library
using GitHub Actions. The pipeline provides automated quality gates (tests,
coverage, linting, type checking, documentation validation), open-source quality
signaling via Codecov, secure package publication to TestPyPI and PyPI using OIDC
trusted publishing, and automated security auditing via pip-audit, CodeQL, and
Dependabot.

## Technical Context

**Language/Version**: Python >=3.10 (test matrix: 3.10, 3.11, 3.12, 3.13)
**Primary Dependencies**: GitHub Actions, Codecov, pip-audit, CodeQL
**Storage**: N/A
**Testing**: pytest + pytest-cov + pytest-bdd (existing), mypy, ruff
**Target Platform**: GitHub Actions (ubuntu-latest runners)
**Project Type**: single (src/ layout, hatchling build backend, uv package manager)
**Performance Goals**: CI pipeline completes within 10 minutes for a typical PR
**Constraints**: Free-tier compatible for open-source, no stored secrets for publishing
**Scale/Scope**: Single Python package (~6 source modules), open-source repository

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. API Compatibility First | N/A | CI/CD does not modify public API |
| II. No Schema Representation Opinion | N/A | CI/CD does not modify dependencies |
| III. Test-First Development | ALIGNED | CI enforces 100% branch coverage (FR-001). Pipeline itself is config-only, not production code |
| IV. Wire Format Fidelity | N/A | CI/CD does not modify wire format code |
| V. Simplicity and Minimal Footprint | ALIGNED | No new runtime dependencies introduced. CI tooling is dev/CI only |
| Quality Standards: Coverage | ALIGNED | CI enforces `--cov-fail-under=100` with branch coverage |
| Quality Standards: Documentation | ALIGNED | FR-016 validates docs build on every PR |
| Development Workflow: IIKit phases | ALIGNED | Following specify → plan → testify → tasks → implement |

## Architecture

```
┌─────────────┐         ┌──────────────────────────────────────┐
│  Developer   │────────▶│           GitHub Repository           │
└─────────────┘         └──────────┬───────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │ push / PR    │ release       │ schedule
                    ▼              ▼               ▼
             ┌──────────┐  ┌────────────┐  ┌────────────┐
             │  ci.yml   │  │publish.yml │  │security.yml│
             └────┬─────┘  └─────┬──────┘  └─────┬──────┘
                  │              │                │
          ┌───┬──┴──┬───┐  ┌────┴────┐     ┌─────┴─────┐
          │   │     │   │  │         │     │           │
        lint type test doc │  TestPyPI│   pip-audit CodeQL
          │   │     │   │  │         │     │           │
          │   │     │   │  │  PyPI   │     │  Dependabot│
          │   │     │   │  └─────────┘     └───────────┘
          │   │     │   │
          │   │     ▼   │
          │   │  Codecov │
          └───┴─────┴───┘
```

## Workflow Design

### 1. CI Workflow (`.github/workflows/ci.yml`)

**Triggers**: push to main, pull requests to main
**Requirements covered**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-016, FR-017

| Job | Python | Purpose | Key Command |
|-----|--------|---------|-------------|
| lint | 3.13 | Static analysis | `uv run ruff check .` |
| typecheck | 3.13 | Type checking | `uv run mypy` |
| test | 3.10-3.13 (matrix) | Tests + coverage | `uv run pytest` |
| docs | 3.13 | Doc build validation | `uv run mkdocs build --strict` |

The `test` job uploads coverage XML as a workflow artifact (FR-006) and sends
results to Codecov (FR-005). All jobs must pass for PR merge (FR-004).

### 2. Publish Workflow (`.github/workflows/publish.yml`)

**Trigger**: GitHub Release published
**Requirements covered**: FR-008, FR-009, FR-010, FR-011, FR-012

Sequential pipeline with hard gates:

1. **validate-version**: Compare `pyproject.toml` version with release tag
2. **build**: `uv build` produces sdist + wheel
3. **publish-testpypi**: OIDC trusted publish to TestPyPI
4. **validate-testpypi**: Install from TestPyPI and run smoke import
5. **publish-pypi**: OIDC trusted publish to PyPI

Each job `needs` the previous one — any failure halts the chain (FR-010).

### 3. Security Workflow (`.github/workflows/security.yml`)

**Triggers**: pull requests to main, weekly schedule (Monday 06:00 UTC)
**Requirements covered**: FR-013, FR-014, FR-015

| Job | Purpose | Tool |
|-----|---------|------|
| dependency-audit | Scan dependency vulnerabilities | pip-audit |
| codeql | Static security analysis | GitHub CodeQL |

### 4. Dependabot Configuration (`.github/dependabot.yml`)

**Trigger**: Daily schedule (pip), weekly schedule (GitHub Actions)
**Requirements covered**: FR-014 (supplementary)

Automatically creates PRs for vulnerable or outdated dependencies.

### 5. Quality Badges (FR-007)

Add to README.md:
- GitHub Actions CI status badge
- Codecov coverage percentage badge

## Project Structure

### Documentation (this feature)

```text
specs/005-ci-cd-pipeline/
  spec.md              # Feature specification
  plan.md              # This file
  research.md          # Technology decisions
  data-model.md        # Workflow data model
  quickstart.md        # Setup guide and test scenarios
  contracts/           # Workflow contracts
    ci-workflow.md
    publish-workflow.md
    security-workflow.md
```

### Source Code (repository root)

```text
.github/
  workflows/
    ci.yml               # Quality gate workflow
    publish.yml          # Package publication workflow
    security.yml         # Security audit workflow
  dependabot.yml         # Dependency update configuration
```

**Structure Decision**: All deliverables are GitHub Actions workflow YAML files
and a Dependabot configuration. No changes to the `src/` or `tests/` directories.
The only change to existing files is adding badges to README.md (if it exists).

## Dependency Analysis

### New Dev/CI Dependencies

| Dependency | Purpose | Where |
|------------|---------|-------|
| pip-audit | Dependency vulnerability scanning | dev dependency group in pyproject.toml |

### External Services (No Code Dependencies)

| Service | Purpose | Setup |
|---------|---------|-------|
| Codecov | Coverage reporting + badges | Install GitHub App |
| GitHub CodeQL | Static security analysis | Enabled via workflow |
| GitHub Dependabot | Scheduled dependency monitoring | Enabled via config |
| TestPyPI | Staging package registry | Configure trusted publisher |
| PyPI | Production package registry | Configure trusted publisher |

### GitHub Actions Used

| Action | Version | Purpose |
|--------|---------|---------|
| actions/checkout | v4 | Repository checkout |
| actions/setup-python | v5 | Python version setup |
| astral-sh/setup-uv | v5 | uv installation |
| actions/upload-artifact | v4 | Coverage report artifact |
| codecov/codecov-action | v5 | Coverage upload |
| pypa/gh-action-pypi-publish | v1 | Trusted PyPI publishing |
| github/codeql-action/init | v3 | CodeQL initialization |
| github/codeql-action/analyze | v3 | CodeQL analysis |
| actions/download-artifact | v4 | Artifact download in publish |

## Implementation Strategy

### Phase 1: CI Quality Gates

Create `ci.yml` with lint, typecheck, test (matrix), and docs jobs. This is the
foundation that all other workflows depend on conceptually (though not technically
via GitHub Actions `needs`).

### Phase 2: Security Auditing

Create `security.yml` with pip-audit and CodeQL. Add pip-audit to dev
dependencies. Create `dependabot.yml`.

### Phase 3: Package Publication

Create `publish.yml` with the full staging-to-production pipeline. Requires
TestPyPI and PyPI trusted publisher configuration (documented in quickstart.md).

### Phase 4: Quality Badges

Add CI status and Codecov badges to README.md.

## Complexity Tracking

No constitution violations requiring justification. All tooling is CI/dev-only
and does not affect the runtime dependency set or public API.
