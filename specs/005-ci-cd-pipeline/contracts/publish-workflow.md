# Contract: Publish Workflow

**File**: `.github/workflows/publish.yml`

## Trigger

```yaml
on:
  release:
    types: [published]
```

## Jobs

### `validate-version`

- **Runner**: ubuntu-latest
- **Steps**: checkout, extract version from pyproject.toml, compare with
  release tag, fail if mismatch
- **Covers**: FR-009

### `build`

- **Runner**: ubuntu-latest
- **Needs**: validate-version
- **Steps**: checkout, setup-python (3.13), install uv, `uv build`
- **Artifacts**: `dist/` (sdist + wheel)
- **Covers**: FR-008 (build step)

### `publish-testpypi`

- **Runner**: ubuntu-latest
- **Needs**: build
- **Environment**: testpypi
- **Permissions**: id-token: write (OIDC)
- **Steps**: download dist artifact, publish to TestPyPI via trusted publishing
- **Covers**: FR-008, FR-011, FR-012

### `validate-testpypi`

- **Runner**: ubuntu-latest
- **Needs**: publish-testpypi
- **Steps**: wait for index propagation, `pip install --index-url
  https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/
  apicurio-serdes=={version}`, run smoke import
- **Covers**: FR-008 (staging validation)

### `publish-pypi`

- **Runner**: ubuntu-latest
- **Needs**: validate-testpypi
- **Environment**: pypi
- **Permissions**: id-token: write (OIDC)
- **Steps**: download dist artifact, publish to PyPI via trusted publishing
- **Covers**: FR-008, FR-010, FR-011, FR-012

## Error Handling

- **Version mismatch** (FR-009): `validate-version` fails with message:
  `Version mismatch: pyproject.toml has X.Y.Z but release tag is vA.B.C`
- **TestPyPI failure** (FR-010): `publish-pypi` has `needs: validate-testpypi`,
  so it never runs if staging fails
- **Duplicate version** (FR-012): PyPI/TestPyPI reject duplicate uploads
  natively; the workflow does not use `--skip-existing`

## Authentication

Uses OIDC trusted publishing (no stored API tokens):
- TestPyPI trusted publisher configured for environment `testpypi`
- PyPI trusted publisher configured for environment `pypi`
