# CI/CD Setup Guide

This guide covers configuring the CI/CD pipeline for the apicurio-serdes
repository, including GitHub secrets, branch protection rules, and external
service integrations.

## Branch Protection Rules

Configure branch protection for the `main` branch in GitHub repository
settings (Settings > Branches > Add rule):

### Required Status Checks

Enable **Require status checks to pass before merging** and add:

| Check Name | What It Validates |
|---|---|
| `CI / lint` | Ruff linting and formatting via pre-commit |
| `CI / typecheck` | mypy strict type checking |
| `CI / test` | pytest with 100% branch coverage |
| `CI / docs-build` | MkDocs documentation build (strict mode) |

### Recommended Settings

- **Require branches to be up to date before merging**: Yes
- **Do not allow bypassing the above settings**: Yes
