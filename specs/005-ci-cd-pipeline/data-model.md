# Data Model: CI/CD Pipeline

**Feature**: 005-ci-cd-pipeline
**Date**: 2026-03-08

## Entities

This feature does not introduce runtime data entities. The "data model" for a
CI/CD pipeline is the structure of workflow definitions, their triggers, and
their input/output contracts.

### Workflow Definition

| Field | Type | Description |
|-------|------|-------------|
| name | string | Human-readable workflow name |
| triggers | list[TriggerEvent] | Events that start the workflow |
| permissions | map[scope, level] | GitHub token permissions |
| jobs | list[Job] | Ordered job definitions |

### TriggerEvent

| Field | Type | Description |
|-------|------|-------------|
| event | enum | push, pull_request, release, schedule |
| branches | list[string] | Branch filter (push/PR only) |
| types | list[string] | Event subtypes (e.g., published for release) |
| cron | string | Cron expression (schedule only) |

### Job

| Field | Type | Description |
|-------|------|-------------|
| id | string | Job identifier |
| name | string | Display name |
| runs-on | string | Runner image |
| needs | list[string] | Job dependency chain |
| strategy.matrix | map | Parameterized dimensions (e.g., python-version) |
| environment | string | GitHub environment (for trusted publishing) |
| permissions | map[scope, level] | Job-level token permissions |
| steps | list[Step] | Ordered step definitions |

### Step

| Field | Type | Description |
|-------|------|-------------|
| name | string | Step display name |
| uses | string | GitHub Action reference (action@version) |
| run | string | Shell command |
| with | map | Action inputs |
| if | string | Conditional expression |

## Relationships

```
Workflow 1──* Job
Job 1──* Step
Job *──* Job (via needs dependency)
Workflow *──* TriggerEvent
Job 0..1── Environment (for trusted publishing)
```

## State Transitions

### CI Workflow State

```
push/PR event
  → checkout
  → setup python (matrix)
  → install dependencies
  → lint (ruff)
  → type check (mypy)
  → test + coverage (pytest)
  → upload coverage artifact
  → upload to Codecov
  → build docs (mkdocs)
  → report status
```

### Publish Workflow State

```
release event (published)
  → checkout
  → validate version match
  → build package (uv build)
  → publish to TestPyPI
  → validate TestPyPI install
  → publish to PyPI
```

### Security Workflow State

```
PR event / schedule
  → checkout
  → setup python
  → pip-audit (dependency scan)
  → CodeQL analysis
  → report findings
```

## Configuration Requirements

### Repository Settings

| Setting | Value | Purpose |
|---------|-------|---------|
| Branch protection on `main` | Require status checks | FR-004 |
| Required checks | ci, security | FR-004 |
| Codecov GitHub App | Installed | FR-005 |
| Dependabot | Enabled | FR-014 |

### Trusted Publishing (PyPI/TestPyPI)

| Field | Value |
|-------|-------|
| Repository owner | jcbianic |
| Repository name | apicurio-serdes |
| Workflow name | publish.yml |
| Environment (PyPI) | pypi |
| Environment (TestPyPI) | testpypi |

### GitHub Environments

| Environment | Purpose | Protection Rules |
|-------------|---------|-----------------|
| testpypi | Staging publication | None (auto-deploy) |
| pypi | Production publication | None (triggered by release) |
