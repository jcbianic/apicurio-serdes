# CI/CD Setup Guide

This guide covers configuring the CI/CD pipeline for the apicurio-serdes
repository, including GitHub secrets, branch protection rules, and external
service integrations.

## Required Secrets

The CI/CD pipeline requires only one GitHub secret:

| Secret Name | Source | Scope | Used By |
|---|---|---|---|
| `TESTPYPI_API_TOKEN` | [TestPyPI](https://test.pypi.org/manage/account/token/) | Project-scoped | `publish-testpypi` job |

### Obtaining TESTPYPI_API_TOKEN

1. Create an account at [test.pypi.org](https://test.pypi.org/account/register/)
2. Go to **Account Settings** > **API tokens**
   ([direct link](https://test.pypi.org/manage/account/token/))
3. Click **Add API token**
4. Set **Token name** to `apicurio-serdes-ci` (or similar)
5. Set **Scope** to **Project: apicurio-serdes** (if the project exists on
   TestPyPI) or **Entire account** for first-time setup
6. Click **Add token** and copy the token (starts with `pypi-`)

### Adding the Secret to GitHub

1. Go to your GitHub repository
2. Navigate to **Settings** > **Secrets and variables** > **Actions**
3. Click **New repository secret**
4. Set **Name** to `TESTPYPI_API_TOKEN`
5. Paste the token value
6. Click **Add secret**

If the secret is missing or expired, the `publish-testpypi` job will fail with
a clear error message indicating the secret name and where to obtain a new one.

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
2. Navigate to **Admin** > **Advanced Settings**
3. Enable **Build pull requests for this project**
4. Save

Once enabled, ReadTheDocs will:

- Build documentation on every push to `main`
- Build preview documentation for every PR and add a status check with a
  preview link
- Build versioned documentation for release tags

## Draft PRs and CI Behavior

The CI pipeline is configured to minimize resource usage for draft PRs:

| CI Job | Runs on Draft PRs | Runs on Ready PRs | Runs on Push to Main |
|---|---|---|---|
| `lint` | Yes | Yes | Yes |
| `typecheck` | No | Yes | Yes |
| `test` | No | Yes | Yes |
| `docs-build` | No | Yes | Yes |
| `publish-testpypi` | No | Yes | No |

### Creating a Draft PR

When opening a PR, select **Create draft pull request** from the dropdown on
the "Create pull request" button. This runs only the lint check, saving CI
resources while your work is in progress.

### Marking Ready for Review

When your PR is ready, click **Ready for review** on the PR page. This triggers
the full CI suite (typecheck, test, docs-build, and publish-testpypi).

## Troubleshooting

### Missing TESTPYPI_API_TOKEN

**Symptom**: The `publish-testpypi` job fails with:

```
::error::TESTPYPI_API_TOKEN secret is not configured.
```

**Fix**: Follow the steps in [Obtaining TESTPYPI_API_TOKEN](#obtaining-testpypi_api_token)
and [Adding the Secret to GitHub](#adding-the-secret-to-github) above.

### Expired TestPyPI Token

**Symptom**: The `publish-testpypi` job fails during the "Publish to TestPyPI"
step with an authentication error.

**Fix**: Generate a new token on
[TestPyPI](https://test.pypi.org/manage/account/token/) and update the
`TESTPYPI_API_TOKEN` secret in GitHub (Settings > Secrets and variables >
Actions > click the secret > Update).

### TestPyPI Version Conflict

**Symptom**: Publish fails with "File already exists" error.

**Fix**: This is unlikely since versions use `github.run_number` (globally
unique). If it occurs, re-run the workflow — the new run number will produce a
unique version.

### ReadTheDocs Build Failure

**Symptom**: ReadTheDocs status check fails on PR.

**Fix**:

1. Click the status check link to view the build log on ReadTheDocs
2. Common causes: missing `mkdocs.yml` references, broken links in docs,
   Python import errors in `mkdocstrings`
3. Run `uv run mkdocs build --strict` locally to reproduce the error

### CI Not Running on Draft PR Marked Ready

**Symptom**: Marking a draft PR as "Ready for review" does not trigger CI.

**Fix**: Verify that `ready_for_review` is listed in the `pull_request` event
types in `.github/workflows/ci.yml`. Push a no-op commit to re-trigger if
needed.
