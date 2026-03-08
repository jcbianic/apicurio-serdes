# Contract: Security Workflow

**File**: `.github/workflows/security.yml`

## Trigger

```yaml
on:
  pull_request:
    branches: [main]
  schedule:
    - cron: "0 6 * * 1"  # Weekly on Monday at 06:00 UTC
```

## Jobs

### `dependency-audit`

- **Runner**: ubuntu-latest
- **Steps**: checkout, setup-python (3.13), install uv, install deps,
  `uv run pip-audit`
- **Covers**: FR-013, FR-014

### `codeql`

- **Runner**: ubuntu-latest
- **Permissions**: security-events: write
- **Steps**: checkout, initialize CodeQL (language: python),
  autobuild, perform CodeQL analysis
- **Covers**: FR-015

## Outputs

- PR status check: dependency-audit, codeql
- CodeQL results visible in GitHub Security tab
- On scheduled runs: findings appear in GitHub Security alerts

## Scheduled Run Behavior (FR-014)

When triggered by schedule:
- Runs against the default branch (main)
- New findings appear in the GitHub Security tab
- Dependabot (configured separately) creates automated PRs for vulnerable
  dependencies

## Dependabot Configuration

**File**: `.github/dependabot.yml`

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "daily"
    open-pull-requests-limit: 5
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

Covers FR-014 supplementary: automated PRs for dependency updates.
