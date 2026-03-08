# Research: CI/CD Pipeline

**Feature**: 005-ci-cd-pipeline
**Date**: 2026-03-08

## Decision 1: CI Platform

**Question**: Which CI/CD platform to use?

**Decision**: GitHub Actions

**Rationale**: The project is hosted on GitHub. GitHub Actions is free for public
repositories with generous runner minutes, natively integrates with PR status
checks (FR-004), supports matrix builds (FR-017), and provides trusted publishing
via OIDC (FR-011). No additional service accounts or integrations needed.

**Alternatives Considered**:
- CircleCI: Good OSS tier but requires external integration for PR status. Extra
  service to maintain.
- GitLab CI: Would require mirroring the repository. Unnecessary complexity.

---

## Decision 2: Coverage Reporting Service

**Question**: Which external coverage service for public dashboards and badges
(FR-005, FR-007)?

**Decision**: Codecov

**Rationale**: Codecov offers a free tier for public open-source repositories with
no restrictions. It provides: PR comment with coverage delta (SC-003), embeddable
badge (FR-007), public dashboard, GitHub status check integration. Upload via the
official `codecov/codecov-action` GitHub Action. Uses tokenless upload for public
repos (no secret configuration needed).

**Alternatives Considered**:
- Coveralls: Similar feature set but less mature GitHub Actions integration. PR
  comments require additional configuration.
- SonarCloud: More comprehensive (includes code quality) but heavier setup.
  Overkill when ruff + mypy already cover linting and type checking.

---

## Decision 3: Security Scanning Tools

**Question**: How to implement dependency vulnerability scanning (FR-013),
scheduled audits (FR-014), and static security analysis (FR-015)?

**Decision**: pip-audit + CodeQL + Dependabot

**Rationale**:
- **pip-audit** (by pypa): Scans Python dependency tree against the PyPI advisory
  database. Lightweight, Python-specific, runs fast. Covers FR-013.
- **GitHub CodeQL**: Free for public repos, GitHub-native. Performs static
  security analysis of Python code. Covers FR-015.
- **GitHub Dependabot**: Built-in to GitHub, zero configuration. Monitors
  dependencies on a schedule and creates automated PRs. Covers FR-014 without
  needing a custom workflow.

**Alternatives Considered**:
- Safety: Was the standard but now requires a commercial license for CI use.
  pip-audit is the pypa-maintained alternative.
- Bandit: Python static security linter. CodeQL covers this with broader scope
  and is already free/native on GitHub.
- Snyk: Excellent tool but requires account setup and token management. pip-audit
  + Dependabot achieves the same without external dependencies.

---

## Decision 4: Package Publication Mechanism

**Question**: How to implement the staging-then-production publish flow (FR-008)
with secure authentication (FR-011)?

**Decision**: GitHub Actions with OIDC trusted publishing to TestPyPI then PyPI

**Rationale**: Both PyPI and TestPyPI support trusted publishing via OIDC. This
eliminates the need for stored API tokens — the GitHub Actions workflow exchanges
a short-lived OIDC token directly with the registry. The workflow triggers on
GitHub Release creation, validates version match (FR-009), publishes to TestPyPI,
installs from TestPyPI to validate, then publishes to PyPI.

**Setup Required**:
- Configure trusted publisher on TestPyPI for the repository
- Configure trusted publisher on PyPI for the repository
- Both require: repository owner, repository name, workflow filename, environment
  name

**Alternatives Considered**:
- API token in GitHub Secrets: Works but secrets can leak. Trusted publishing is
  the PyPA-recommended approach as of 2024.
- Manual twine upload: Defeats the purpose of automation.

---

## Decision 5: Python Version Matrix

**Question**: Which Python versions to test (FR-017)?

**Decision**: Python 3.10, 3.11, 3.12, 3.13

**Rationale**: The project declares `requires-python = ">=3.10"` in
pyproject.toml. Testing all currently supported CPython versions (3.10 through
3.13) ensures compatibility claims are verified. Python 3.9 reached EOL in
October 2025. Python 3.14 is not yet released.

---

## Decision 6: Documentation Build Validation

**Question**: How to validate documentation builds (FR-016)?

**Decision**: `uv run mkdocs build --strict` in CI

**Rationale**: The project already uses mkdocs with mkdocs-material and
mkdocstrings. Running `mkdocs build --strict` fails on any warning (broken
references, missing docstrings, syntax errors). This validates documentation
buildability without deploying it. ReadTheDocs handles actual hosting/deployment
separately.

**Prerequisite**: A minimal `mkdocs.yml` configuration file and a `docs/`
directory must exist. If not present, the CI step should be added but will need
the docs infrastructure to be set up in a separate feature.

---

## Decision 7: Build Tool

**Question**: Which tool to use for building distribution packages?

**Decision**: `uv build` with hatchling backend

**Rationale**: The project already uses uv as the package manager (uv.lock
present) and hatchling as the build backend. `uv build` produces both sdist and
wheel. No additional tools needed.

---

## Decision 8: Workflow Organization

**Question**: How many workflow files, and what does each cover?

**Decision**: Three workflow files + one Dependabot configuration

| File | Trigger | Covers |
|------|---------|--------|
| `.github/workflows/ci.yml` | push, pull_request | FR-001 through FR-007, FR-016, FR-017 |
| `.github/workflows/publish.yml` | release (published) | FR-008 through FR-012 |
| `.github/workflows/security.yml` | pull_request, schedule (weekly) | FR-013, FR-014, FR-015 |
| `.github/dependabot.yml` | scheduled (daily) | FR-014 (supplementary) |

**Rationale**: Each workflow has a clear responsibility boundary. The CI workflow
handles all quality gates that block PR merges. The publish workflow handles
release distribution. The security workflow handles vulnerability detection both
on-demand and on schedule. Dependabot provides the scheduled dependency monitoring
that creates actionable PRs automatically.
