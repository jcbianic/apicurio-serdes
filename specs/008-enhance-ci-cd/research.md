# Research: Enhance CI/CD Pipeline

**Feature**: 008-enhance-ci-cd | **Date**: 2026-03-09

## Decision Log

### D1: CI Linting Alignment Strategy

**Question**: How to guarantee identical ruff rules between pre-commit and CI (FR-001, FR-002, FR-003)?

**Decision**: CI runs `pre-commit run --all-files` via the `pre-commit/action@v3.0.1` GitHub Action.

**Rationale**: Using pre-commit as the single source of truth for linting in both local and CI environments eliminates alignment drift by design. Both environments execute the same `.pre-commit-config.yaml` with the same pinned ruff version. FR-003 (fail if rules differ) is satisfied trivially because there is only one rule source.

**Alternatives Considered**:
- *Run ruff directly in CI alongside pre-commit locally*: Two configuration sources to maintain; drift risk violates FR-003.
- *Use a shared ruff config file imported by both*: Extra indirection; pre-commit already handles version pinning and execution.

---

### D2: Pre-commit Hook Configuration

**Question**: Which ruff hooks and what version to pin?

**Decision**: Pin `ruff-pre-commit` to `v0.15.5` (matching `uv.lock`) with two hooks: `ruff` (lint with `--fix`) and `ruff-format` (formatting).

**Rationale**: The lock file resolves ruff to 0.15.5. Pinning the pre-commit hook to the same version ensures byte-identical behavior. The `--fix` flag on lint allows auto-fixable issues to be corrected on commit, reducing friction. The `ruff-format` hook replaces `black` with zero configuration.

**Rules applied** (from `pyproject.toml`):
- Select: `["E", "F", "I", "N", "W", "UP", "B", "SIM", "TCH"]`
- Target: Python 3.10
- Line length: 88
- Per-file ignores: `tests/**` ignores `E501`, `TCH`

These rules live in `pyproject.toml` and are consumed by ruff automatically. No duplication needed in `.pre-commit-config.yaml`.

---

### D3: TestPyPI Publishing Mechanism

**Question**: How to publish pre-release packages to TestPyPI on PR (FR-004, FR-005)?

**Decision**: Use `pypa/gh-action-pypi-publish@release/v1` with a `TESTPYPI_API_TOKEN` stored as a GitHub repository secret.

**Rationale**: The official PyPA publish action is the community standard for publishing Python packages from GitHub Actions. Using an API token (scoped to the `apicurio-serdes` project on TestPyPI) is simpler to set up than Trusted Publishers for a first-time CI/CD pipeline and matches the spec's explicit mention of API key secrets.

**Alternatives Considered**:
- *Trusted Publishers (OIDC)*: More secure (no stored secret), but requires TestPyPI dashboard configuration and OIDC token permissions. Recommended as a future enhancement once the pipeline is proven stable.
- *twine upload*: Lower-level; the PyPA action wraps twine with better error handling and attestation support.

---

### D4: Pre-release Version Management

**Question**: How to generate unique `X.Y.ZrcN` versions for TestPyPI (FR-004)?

**Decision**: Override version in `pyproject.toml` during CI build using `sed`, setting version to `{base_version}rc{github.run_number}`.

**Rationale**: `github.run_number` is globally unique and monotonically increasing within a repository, preventing version conflicts even with parallel PRs (edge case from spec). The version override is ephemeral (CI workspace only, never committed). PEP 440 `rc` suffix is a standard release-candidate marker that sorts correctly in pip.

**Example**: Base version `0.1.0` + run number `42` = `0.1.0rc42`.

**Alternatives Considered**:
- *PR number as suffix*: `0.1.0rc{PR_NUMBER}` — conflicts when a PR triggers multiple runs (updated commits).
- *Git SHA suffix*: Not PEP 440 compliant for `rcN` format.
- *hatch-vcs plugin*: Adds a build dependency; overkill for a simple override.

---

### D5: Documentation Build and Publishing

**Question**: How to build and publish docs on PR and release (FR-006, FR-007, FR-008)?

**Decision**: Use ReadTheDocs native GitHub integration (webhook-based) with `.readthedocs.yaml` in the repo. Additionally, run `mkdocs build --strict` in CI as a fast validation gate.

**Rationale**: RTD's native GitHub integration automatically builds docs on push and provides PR preview links via status checks — satisfying FR-006 without any GitHub secret. The CI docs-build job provides faster feedback (fails in minutes vs. RTD's queue). Both serve as quality gates.

**Configuration**:
- RTD dashboard: connect GitHub repo, enable PR builds
- `.readthedocs.yaml`: specifies Python version, build commands, mkdocs config
- `mkdocs.yml`: site configuration, theme, plugins

**Alternatives Considered**:
- *RTD API from GitHub Actions*: Requires `READTHEDOCS_TOKEN` secret; more complex with no benefit over native integration.
- *GitHub Pages*: Simpler but lacks PR preview builds and version management.
- *Netlify*: Good PR previews but adds another service; RTD is purpose-built for Python docs.

---

### D6: Draft PR and Conditional CI

**Question**: How to skip/minimize CI on draft PRs (FR-011, FR-012, FR-013)?

**Decision**: Use `github.event.pull_request.draft == false` condition on heavy CI jobs. Lint job runs always (fast feedback); typecheck, test, docs-build, and publish run only on non-draft PRs.

**Rationale**: The `pull_request.ready_for_review` event type triggers when a PR transitions from draft to ready, ensuring the full suite runs at that transition. Running lint on drafts gives developers quick feedback on formatting without consuming significant CI resources.

**Workflow trigger configuration**:
```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
  push:
    branches: [main]
```

**Job conditions**:
- `lint`: always runs (fast, ~30s)
- `typecheck`, `test`, `docs-build`: `if: github.event.pull_request.draft == false || github.event_name == 'push'`
- `publish-testpypi`: `needs: [lint, typecheck, test]` + non-draft + PR only

---

### D7: Quality Gates and Status Checks

**Question**: Which status checks to require for merge (FR-010, FR-014)?

**Decision**: Four required status checks from CI workflow + one from ReadTheDocs:

| Status Check | Source | What It Validates |
|---|---|---|
| `CI / lint` | ci.yml | Ruff lint + format via pre-commit |
| `CI / typecheck` | ci.yml | mypy --strict |
| `CI / test` | ci.yml | pytest with 100% branch coverage |
| `CI / docs-build` | ci.yml | mkdocs build --strict |
| `docs/readthedocs.org:*` | ReadTheDocs | Documentation preview build |

**Branch protection** (configured via GitHub UI):
- Require status checks to pass before merging
- Require branches to be up to date before merging
- Require pull request reviews (recommended, not in spec)

---

### D8: Secrets Configuration

**Question**: What secrets are required and how to keep them minimal (FR-009)?

**Decision**: One required secret: `TESTPYPI_API_TOKEN`.

| Secret Name | Purpose | Where to Obtain |
|---|---|---|
| `TESTPYPI_API_TOKEN` | Publish pre-release packages to TestPyPI | TestPyPI account > API tokens > Add token (scoped to `apicurio-serdes`) |

**Rationale**: ReadTheDocs uses webhook-based authentication (configured in RTD dashboard, not GitHub). This minimizes secrets to a single API token, satisfying FR-009.

---

### D9: CI Runner and Python Version

**Question**: What runner OS and Python version to use?

**Decision**: `ubuntu-latest` runner, Python 3.10 (minimum supported version from `requires-python`).

**Rationale**: Testing against the minimum supported version catches backward-compatibility issues. Ubuntu is the standard GitHub Actions runner. Multi-version matrix testing (3.10, 3.11, 3.12, 3.13) is a potential enhancement but not in scope for this feature.

---

### D10: Package Manager in CI

**Question**: pip, pip-tools, or uv for dependency installation in CI?

**Decision**: Use `uv` via `astral-sh/setup-uv@v5` action.

**Rationale**: The project already uses uv as its package manager (uv.lock exists). Using uv in CI ensures identical dependency resolution. The `setup-uv` action handles installation and caching. uv is significantly faster than pip for dependency resolution and installation.

---

## Tessl Tiles

Tessl CLI was not responsive during tile discovery. Existing installed tiles (from `tessl.json`):

### Installed Tiles

| Technology | Tile | Type | Version |
|---|---|---|---|
| httpx | tessl/pypi-httpx | docs | 0.28.0 |
| pytest | tessl/pypi-pytest | docs | 8.4.0 |
| pytest-cov | tessl/pypi-pytest-cov | docs | 6.2.0 |

### Technologies Without Tiles

- GitHub Actions: No tile found
- pre-commit: No tile found
- ruff: No tile found
- mkdocs: No tile found
- ReadTheDocs: No tile found
- hatchling: No tile found
