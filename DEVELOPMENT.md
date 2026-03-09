# Development and release guide

This document is for project maintainers.

## Cutting a release

1. Update `version` in `pyproject.toml` and `src/apicurio_serdes/_version.py`.
2. Update `CHANGELOG.md` — move items from `Unreleased` to the new version section.
3. Commit: `git commit -m "chore: release vX.Y.Z"`.
4. Push to `main`, then create a GitHub Release with tag `vX.Y.Z`.
5. The publish workflow runs automatically: TestPyPI → smoke test → PyPI.
