# Development and release guide

This document is for project maintainers.

## Complexity tracking

Complexity is enforced in CI via **Xenon** and tracked over time with **Wily**.

### Xenon — CI gate

Xenon runs automatically on every PR. Thresholds (calibrated from the v0.4.0 baseline):

| Flag | Threshold | What it checks |
|---|---|---|
| `--max-absolute` | C | Worst single block in the codebase |
| `--max-modules` | B | Worst module-level average |
| `--max-average` | A | Mean across all blocks |

Run locally with `uv run xenon --max-absolute C --max-modules B --max-average A src/`.

### Wily — trend analysis

Wily tracks complexity metrics across commits. Build the history index and inspect trends before or after a feature branch:

```bash
# Build the history index (run once, or after new commits)
uv run wily build src/

# Report complexity trend for a specific file
uv run wily report src/apicurio_serdes/avro/_serializer.py

# Diff complexity between the current branch and main
uv run wily diff src/ -r main
```

Run `uv run wily report src/` before opening a PR to check for regressions introduced by your changes.

## Cutting a release

1. Update `version` in `pyproject.toml` and `src/apicurio_serdes/_version.py`.
2. Update `CHANGELOG.md` — move items from `Unreleased` to the new version section.
3. Commit: `git commit -m "chore: release vX.Y.Z"`.
4. Push to `main`, then create a GitHub Release with tag `vX.Y.Z`.
5. The publish workflow runs automatically: TestPyPI → smoke test → PyPI.
