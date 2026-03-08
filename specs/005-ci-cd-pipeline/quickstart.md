# Quickstart: CI/CD Pipeline

**Feature**: 005-ci-cd-pipeline
**Date**: 2026-03-08

## Setup Checklist

### 1. Repository Configuration

After merging the workflow files, configure the repository:

- [ ] Enable branch protection on `main` with required status checks
- [ ] Mark `ci` and `security` as required checks
- [ ] Install the Codecov GitHub App on the repository
- [ ] Enable Dependabot alerts in repository settings

### 2. Trusted Publishing Setup

Configure OIDC trusted publishers on both registries:

**TestPyPI** (https://test.pypi.org/manage/project/apicurio-serdes/settings/publishing/):
- Repository owner: `jcbianic`
- Repository name: `apicurio-serdes`
- Workflow name: `publish.yml`
- Environment name: `testpypi`

**PyPI** (https://pypi.org/manage/project/apicurio-serdes/settings/publishing/):
- Repository owner: `jcbianic`
- Repository name: `apicurio-serdes`
- Workflow name: `publish.yml`
- Environment name: `pypi`

### 3. GitHub Environments

Create two environments in the repository settings:
- `testpypi` — no protection rules
- `pypi` — no protection rules (release trigger provides the gate)

### 4. Documentation Infrastructure

Ensure the following exist before the docs validation step will pass:
- `mkdocs.yml` configuration file
- `docs/` directory with at least an `index.md`

## Test Scenarios

### Scenario 1: CI Quality Gate (Happy Path)

1. Create a branch, make a valid code change, push
2. Open a pull request
3. Verify: all CI checks pass (lint, typecheck, test, coverage, docs)
4. Verify: Codecov posts a coverage summary comment on the PR
5. Verify: PR shows green status checks

### Scenario 2: CI Quality Gate (Failure)

1. Push a commit with a type error
2. Verify: mypy check fails, PR is blocked
3. Push a commit with a failing test
4. Verify: pytest check fails, PR is blocked
5. Push a commit that drops coverage below 100%
6. Verify: coverage check fails, PR is blocked

### Scenario 3: Publication (Happy Path)

1. Update version in `pyproject.toml` to a new version (e.g., `0.2.0`)
2. Create a GitHub Release with tag `v0.2.0`
3. Verify: publish workflow triggers
4. Verify: version validation passes (tag matches pyproject.toml)
5. Verify: package appears on TestPyPI
6. Verify: package appears on PyPI

### Scenario 4: Publication (Version Mismatch)

1. Set version in `pyproject.toml` to `0.3.0`
2. Create a GitHub Release with tag `v0.4.0`
3. Verify: publish workflow fails at version validation step

### Scenario 5: Security Audit

1. Open a PR that adds a dependency with a known vulnerability
2. Verify: pip-audit reports the vulnerability
3. Verify: security check fails on the PR

### Scenario 6: Multi-Python Compatibility

1. Open a PR with any code change
2. Verify: test matrix runs on Python 3.10, 3.11, 3.12, 3.13
3. Verify: each version reports independently

### Scenario 7: Quality Badges

1. After CI runs on `main`, visit the repository README
2. Verify: CI status badge shows "passing"
3. Verify: Codecov badge shows current coverage percentage
