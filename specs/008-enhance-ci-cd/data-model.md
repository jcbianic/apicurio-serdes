# Data Model: Enhance CI/CD Pipeline

**Feature**: 008-enhance-ci-cd | **Date**: 2026-03-09

This feature is infrastructure-focused (CI/CD configuration). The "data model" describes
configuration entities and their relationships rather than application data.

## Configuration Entities

### Pre-commit Configuration (`.pre-commit-config.yaml`)

| Field | Type | Description |
|---|---|---|
| repos | list | Hook repository definitions |
| repos[].repo | URL | Hook source repository |
| repos[].rev | string | Pinned version tag (must match uv.lock ruff version) |
| repos[].hooks | list | Hook definitions within repo |

**Relationships**: Consumed by pre-commit CLI (local) and `pre-commit/action` (CI).
Ruff rules sourced from `pyproject.toml [tool.ruff]` — no duplication.

**Validation**: `repos[].rev` must match ruff version in `uv.lock` (currently `v0.15.5`).

---

### CI Workflow (`.github/workflows/ci.yml`)

| Field | Type | Description |
|---|---|---|
| name | string | Workflow display name |
| on.pull_request.types | list | Event types: opened, synchronize, reopened, ready_for_review |
| on.push.branches | list | Push trigger branches: [main] |
| jobs | map | Job definitions |

**Jobs**:

| Job | Condition | Dependencies |
|---|---|---|
| lint | always | none |
| typecheck | non-draft or push | none |
| test | non-draft or push | none |
| docs-build | non-draft or push | none |
| publish-testpypi | non-draft + PR only | lint, typecheck, test |

**Relationships**: Produces GitHub status checks consumed by branch protection rules.

---

### ReadTheDocs Configuration (`.readthedocs.yaml`)

| Field | Type | Description |
|---|---|---|
| version | int | Config version (2) |
| build.os | string | Build OS (ubuntu-24.04) |
| build.tools.python | string | Python version (3.10) |
| mkdocs.configuration | path | Path to mkdocs.yml |
| build.commands | list | Custom build commands (uv sync, mkdocs build) |

**Relationships**: Read by ReadTheDocs on webhook trigger. References `mkdocs.yml`.

---

### MkDocs Configuration (`mkdocs.yml`)

| Field | Type | Description |
|---|---|---|
| site_name | string | "apicurio-serdes" |
| theme.name | string | "material" |
| plugins | list | search, mkdocstrings |
| nav | list | Navigation structure |

**Relationships**: Consumed by `mkdocs build` (CI) and ReadTheDocs. References `docs/` directory.

---

### GitHub Secrets

| Entity | Type | Description |
|---|---|---|
| TESTPYPI_API_TOKEN | secret string | API token scoped to apicurio-serdes on TestPyPI |

**Relationships**: Consumed by `publish-testpypi` job in CI workflow.

---

### Branch Protection Rules

| Setting | Value | Description |
|---|---|---|
| required_status_checks | lint, typecheck, test, docs-build | Must pass before merge |
| require_up_to_date | true | Branch must be current with base |
| enforce_admins | true | Rules apply to admins too |

**Relationships**: Consumes status checks produced by CI workflow and ReadTheDocs.

## Entity Relationship Summary

```
pyproject.toml [tool.ruff]
       │ rules
       ▼
.pre-commit-config.yaml ────▶ pre-commit/action (CI lint job)
       │                              │
       │ local                        │ status check
       ▼                              ▼
Developer workstation          Branch Protection Rules
                                      ▲
ci.yml ──────────────────────────────┘
  │         │ status checks (typecheck, test, docs-build)
  │         │
  │    publish-testpypi job ──▶ TestPyPI (TESTPYPI_API_TOKEN)
  │
mkdocs.yml ◀── .readthedocs.yaml ──▶ ReadTheDocs (webhook)
  │                                        │
  ▼                                        │ status check
docs/ ─────────────────────────────────────┘
```
