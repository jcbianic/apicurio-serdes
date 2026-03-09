# CI/CD Interface Contracts

**Feature**: 008-enhance-ci-cd | **Date**: 2026-03-09

## Workflow: ci.yml

### Trigger Contract

| Event | Types | Condition |
|---|---|---|
| `pull_request` | opened, synchronize, reopened, ready_for_review | all branches |
| `push` | — | branches: [main] |

### Job Contracts

#### Job: `lint`

| Property | Value |
|---|---|
| Name | `CI / lint` |
| Runs on | ubuntu-latest |
| Condition | always (drafts included) |
| Tool | pre-commit/action@v3.0.1 |
| Python | 3.10 |
| Pass criteria | `pre-commit run --all-files` exits 0 |
| Output | GitHub status check `CI / lint` |

#### Job: `typecheck`

| Property | Value |
|---|---|
| Name | `CI / typecheck` |
| Runs on | ubuntu-latest |
| Condition | `github.event.pull_request.draft == false \|\| github.event_name == 'push'` |
| Tool | uv run mypy |
| Python | 3.10 |
| Pass criteria | `mypy --strict` exits 0 |
| Output | GitHub status check `CI / typecheck` |

#### Job: `test`

| Property | Value |
|---|---|
| Name | `CI / test` |
| Runs on | ubuntu-latest |
| Condition | `github.event.pull_request.draft == false \|\| github.event_name == 'push'` |
| Tool | uv run pytest |
| Python | 3.10 |
| Pass criteria | pytest exits 0 (implies 100% branch coverage via --cov-fail-under=100) |
| Output | GitHub status check `CI / test` |

#### Job: `docs-build`

| Property | Value |
|---|---|
| Name | `CI / docs-build` |
| Runs on | ubuntu-latest |
| Condition | `github.event.pull_request.draft == false \|\| github.event_name == 'push'` |
| Tool | uv run mkdocs build --strict |
| Python | 3.10 |
| Pass criteria | mkdocs build exits 0 with no warnings |
| Output | GitHub status check `CI / docs-build` |

#### Job: `publish-testpypi`

| Property | Value |
|---|---|
| Name | `CI / publish-testpypi` |
| Runs on | ubuntu-latest |
| Condition | PR event + non-draft + all quality gates pass |
| Needs | lint, typecheck, test |
| Secret | `TESTPYPI_API_TOKEN` |
| Tool | pypa/gh-action-pypi-publish@release/v1 |
| Version format | `{base_version}rc{github.run_number}` (PEP 440) |
| Pass criteria | package uploaded to TestPyPI |
| Output | GitHub status check `CI / publish-testpypi` |

### Version Override Contract

```
Input:  pyproject.toml version = "X.Y.Z"
Transform: sed "s/version = \"X.Y.Z\"/version = \"X.Y.ZrcN\"/"
  where N = github.run_number
Output: dist/apicurio_serdes-X.Y.ZrcN-py3-none-any.whl
        dist/apicurio_serdes-X.Y.ZrcN.tar.gz
Target: https://test.pypi.org/legacy/
```

## External Service: ReadTheDocs

### Integration Contract

| Property | Value |
|---|---|
| Trigger | Webhook on push/PR (configured in RTD dashboard) |
| Config file | `.readthedocs.yaml` |
| Build tool | mkdocs (via uv) |
| PR builds | Enabled in RTD dashboard |
| Output | Status check on PR with preview link |
| Release builds | Triggered by push to main or tag |
| Authentication | Webhook-based (no GitHub secret) |

## Secrets Contract

| Secret Name | Required | Scope | Used By |
|---|---|---|---|
| `TESTPYPI_API_TOKEN` | Yes | Project: apicurio-serdes | publish-testpypi job |

No other secrets, environment variables, or hardcoded configuration values
are required (FR-009).

## Branch Protection Contract

### Required Status Checks

| Check Name | Source | Required |
|---|---|---|
| `CI / lint` | ci.yml | Yes |
| `CI / typecheck` | ci.yml | Yes |
| `CI / test` | ci.yml | Yes |
| `CI / docs-build` | ci.yml | Yes |

### Settings

| Setting | Value |
|---|---|
| Require status checks to pass | Yes |
| Require branches to be up to date | Yes |
| Enforce for admins | Yes |

## Pre-commit Hook Contract

### Local Execution

```
Trigger: git commit
Hooks:
  1. ruff (lint with --fix, auto-correct fixable issues)
  2. ruff-format (format check)
Config: .pre-commit-config.yaml
Rules: pyproject.toml [tool.ruff]
Version: ruff v0.15.5 (pinned, must match uv.lock)
```

### CI Execution

```
Trigger: ci.yml lint job
Action: pre-commit/action@v3.0.1
Behavior: pre-commit run --all-files (no --fix, check-only)
Config: same .pre-commit-config.yaml
Result: identical to local execution
```
