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

## ReadTheDocs Integration

ReadTheDocs builds documentation automatically via webhook (no GitHub secret
required).

### Initial Setup

1. Log in to [readthedocs.org](https://readthedocs.org)
2. Click **Import a Project**
3. Connect your GitHub account and select `apicurio-serdes`
4. ReadTheDocs will auto-configure a webhook on your GitHub repository

### Enable PR Preview Builds

1. Go to the project on ReadTheDocs
2. Navigate to **Admin > Advanced Settings**
3. Enable **Build pull requests for this project**
4. Save

Once enabled, ReadTheDocs will:

- Build documentation on every push to `main`
- Build preview documentation for every PR and add a status check with a
  preview link
- Build versioned documentation for release tags
