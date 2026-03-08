# CI/CD Pipeline

This page documents the continuous integration and delivery pipeline for
apicurio-serdes.

## Pipeline Architecture

The pipeline consists of three GitHub Actions workflows and a Dependabot
configuration:

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | Push to main, pull requests | Quality gates (lint, typecheck, test, docs) |
| `publish.yml` | GitHub Release published | Package publication to TestPyPI → PyPI |
| `security.yml` | Push to main, pull requests, weekly schedule | Vulnerability scanning and CodeQL analysis |
| `dependabot.yml` | Daily (pip), weekly (Actions) | Automated dependency update PRs |

## CI Workflow

Every push to `main` and every pull request triggers four parallel jobs:

- **lint** — Runs `ruff check .` for static analysis
- **typecheck** — Runs `mypy` for type checking
- **test** — Runs `pytest` with 100% branch coverage enforcement across Python
  3.10, 3.11, 3.12, and 3.13
- **docs** — Runs `mkdocs build --strict` to validate documentation builds

All four jobs must pass for a PR to be mergeable.

### Coverage Reporting

The test job uploads coverage results to [Codecov](https://codecov.io). Codecov
provides:

- A coverage percentage badge in the README
- PR comments showing coverage delta vs. the base branch
- A public dashboard for the repository

The Codecov upload is non-blocking — if the Codecov service is unavailable, CI
still passes or fails based on local coverage enforcement.

## Publish Workflow

The publish workflow triggers when a GitHub Release is created. It runs a
sequential pipeline with hard gates:

1. **validate-version** — Compares the release tag (e.g., `v0.2.0`) with the
   version in `pyproject.toml`. Fails if they don't match.
2. **build** — Runs `uv build` to produce sdist and wheel distributions.
3. **publish-testpypi** — Publishes to TestPyPI using OIDC trusted publishing.
4. **validate-testpypi** — Installs from TestPyPI and runs a smoke import test.
5. **publish-pypi** — Publishes to PyPI using OIDC trusted publishing.

Each step requires the previous one to succeed. A failure at any stage halts the
pipeline.

### Trusted Publishing Setup

The publish workflow uses OIDC trusted publishing — no stored API tokens are
needed. Configure trusted publishers on both registries:

**TestPyPI** (`https://test.pypi.org/manage/project/apicurio-serdes/settings/publishing/`):

- Repository owner: `jcbianic`
- Repository name: `apicurio-serdes`
- Workflow name: `publish.yml`
- Environment name: `testpypi`

**PyPI** (`https://pypi.org/manage/project/apicurio-serdes/settings/publishing/`):

- Repository owner: `jcbianic`
- Repository name: `apicurio-serdes`
- Workflow name: `publish.yml`
- Environment name: `pypi`

Create two GitHub environments in the repository settings: `testpypi` and `pypi`.

## Security Workflow

Runs on every push to `main`, every PR to `main`, and on a weekly schedule
(Monday 06:00 UTC):

- **dependency-audit** — Runs `pip-audit` to scan for known vulnerabilities in
  the dependency tree
- **codeql** — Runs GitHub CodeQL static security analysis for Python

### Dependabot

Dependabot monitors dependencies and creates automated update PRs:

- **pip** ecosystem: checked daily
- **github-actions** ecosystem: checked weekly

## Quality Badges

The README displays two badges:

- **CI status** — Shows whether the latest CI run on `main` passed or failed
- **Codecov** — Shows the current coverage percentage

## Release Process

1. Update the version in `pyproject.toml` (e.g., `0.2.0`)
2. Commit and merge to `main`
3. Create a GitHub Release with tag matching the version (e.g., `v0.2.0`)
4. The publish workflow automatically handles TestPyPI → PyPI publication

## Initial Setup Checklist

After merging the workflow files:

- [ ] Enable branch protection on `main` with required status checks
- [ ] Mark `lint`, `typecheck`, `test`, and `docs` as required checks
- [ ] Install the [Codecov GitHub App](https://github.com/apps/codecov) on the
  repository
- [ ] Configure trusted publishers on TestPyPI and PyPI (see above)
- [ ] Create `testpypi` environment in repository settings (no protection rules)
- [ ] Create `pypi` environment in repository settings with at least one required
  reviewer (production publication gate)
- [ ] Enable Dependabot alerts in repository settings
