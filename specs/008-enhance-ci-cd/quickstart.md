# Quickstart: CI/CD Pipeline Setup

**Feature**: 008-enhance-ci-cd | **Date**: 2026-03-09

## Prerequisites

- GitHub repository with admin access
- TestPyPI account (https://test.pypi.org)
- ReadTheDocs account (https://readthedocs.org)
- Python 3.10+ with uv installed locally

## Setup Steps

### 1. Install Pre-commit Hooks Locally

```bash
# Install pre-commit (if not already installed)
uv tool install pre-commit

# Install hooks from .pre-commit-config.yaml
pre-commit install

# Verify hooks work
pre-commit run --all-files
```

**Test scenario**: Create a file with a ruff violation (e.g., unused import), run
`git commit`, verify pre-commit blocks the commit.

### 2. Configure GitHub Secret

Add the following secret to your GitHub repository
(Settings > Secrets and variables > Actions > New repository secret):

| Secret Name | Value |
|---|---|
| `TESTPYPI_API_TOKEN` | API token from TestPyPI (scoped to `apicurio-serdes` project) |

**To obtain the token**:
1. Log in to https://test.pypi.org
2. Go to Account Settings > API tokens
3. Click "Add API token"
4. Scope: Project `apicurio-serdes` (create the project first if needed)
5. Copy the token (starts with `pypi-`)

**Test scenario**: Push a branch, open a non-draft PR, verify the `publish-testpypi`
job succeeds and the package appears on TestPyPI.

### 3. Connect ReadTheDocs

1. Log in to https://readthedocs.org
2. Click "Import a Project"
3. Connect your GitHub account and select `apicurio-serdes`
4. Enable "Build pull requests" in Admin > Advanced Settings
5. ReadTheDocs will auto-configure a webhook on your GitHub repo

**Test scenario**: Open a PR with documentation changes, verify ReadTheDocs builds
and adds a status check with a preview link.

### 4. Configure Branch Protection

In GitHub repository Settings > Branches > Add rule for `main`:

- [x] Require status checks to pass before merging
  - Required checks: `CI / lint`, `CI / typecheck`, `CI / test`, `CI / docs-build`
- [x] Require branches to be up to date before merging
- [x] Do not allow bypassing the above settings

**Test scenario**: Open a PR where tests fail, verify the merge button is disabled.

### 5. Verify End-to-End

1. Create a feature branch with a small change
2. Run `pre-commit run --all-files` locally — should pass
3. Push and open a PR as **draft**
4. Verify: only `CI / lint` runs, other jobs are skipped
5. Mark the PR as "Ready for Review"
6. Verify: all CI jobs run (lint, typecheck, test, docs-build)
7. Verify: TestPyPI package is published
8. Verify: ReadTheDocs preview link appears as a status check
9. Verify: merge button is enabled only when all checks pass

## Troubleshooting

### Pre-commit hook version mismatch

If CI lint fails but local pre-commit passes, the ruff version in
`.pre-commit-config.yaml` may not match `uv.lock`. Update the `rev` field
to match:

```bash
grep 'version = "0' uv.lock | grep ruff  # Find locked version
# Update .pre-commit-config.yaml rev to match
```

### TestPyPI publish fails with 403

The `TESTPYPI_API_TOKEN` is likely expired or mis-scoped. Generate a new
token scoped to the `apicurio-serdes` project on TestPyPI.

### TestPyPI version conflict

If a version already exists on TestPyPI, the publish will fail. This should
not happen with `run_number`-based versioning, but if it does, re-run the
CI workflow (which increments run_number).

### ReadTheDocs build fails

Check `.readthedocs.yaml` syntax and ensure `mkdocs.yml` references valid
documentation files in `docs/`.

### Missing secret error in CI

The workflow logs will show which secret is missing. Refer to step 2 above
to add it.
