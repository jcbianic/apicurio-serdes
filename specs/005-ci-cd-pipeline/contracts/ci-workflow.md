# Contract: CI Workflow

**File**: `.github/workflows/ci.yml`

## Trigger

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

## Jobs

### `lint`

- **Runner**: ubuntu-latest
- **Steps**: checkout, setup-python (3.13), install uv, install deps, `uv run ruff check .`
- **Covers**: FR-002

### `typecheck`

- **Runner**: ubuntu-latest
- **Steps**: checkout, setup-python (3.13), install uv, install deps, `uv run mypy`
- **Covers**: FR-003

### `test`

- **Runner**: ubuntu-latest
- **Strategy**: matrix python-version [3.10, 3.11, 3.12, 3.13]
- **Steps**: checkout, setup-python (matrix), install uv, install deps,
  `uv run pytest`, upload coverage artifact (XML), upload to Codecov
- **Covers**: FR-001, FR-005, FR-006, FR-017
- **Artifacts**: `coverage-report-{python-version}` (coverage XML)

### `docs`

- **Runner**: ubuntu-latest
- **Steps**: checkout, setup-python (3.13), install uv, install deps,
  `uv run mkdocs build --strict`
- **Covers**: FR-016

## Outputs

- PR status checks: lint, typecheck, test (per matrix), docs
- Coverage report uploaded to Codecov (tokenless for public repos)
- Coverage XML artifact downloadable from workflow run

## Required Status Checks (FR-004)

All jobs must pass for PR merge. Configure in repository branch protection:
- `lint`
- `typecheck`
- `test` (all matrix entries)
- `docs`
