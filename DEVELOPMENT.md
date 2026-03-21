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

Wily tracks complexity metrics across commits and is the right tool for assessing
whether a PR improves or worsens maintainability.

#### Setup (once per machine)

```bash
# Index the full git history — run once, or after rebasing
uv run wily build src/
```

This reads the git log and snapshots metrics for every commit. The index is stored in
`.wily/` (gitignored). It only needs to be re-run when you want to include new commits
that aren't yet indexed.

#### PR assessment workflow

Before opening a PR, run a diff against the release branch:

```bash
uv run wily diff src/ -r release/v0.5.0
```

This compares the files **on disk** against the indexed state of `release/v0.5.0`.
Only files that changed are shown. Metrics that improved are highlighted green,
regressions are red.

Example output (this PR):

```
_strategies.py   MI: 39.46 → 52.45   LOC: 183 → 153
```

#### Two commands, two purposes

| Command | What it shows | When to use |
|---|---|---|
| `wily diff src/ -r <base>` | Before→after for changed files only | PR assessment |
| `wily report src/apicurio_serdes/_base.py` | Per-file history over all indexed commits | Investigating a file's trajectory |

#### Important: `report` is file-scoped, not directory-scoped

`wily report src/` does **not** aggregate all files — it looks for a literal file
named `src/` in the index and returns nothing useful. Always pass a specific file path
to `report`:

```bash
# Correct
uv run wily report src/apicurio_serdes/_base.py

# Wrong — returns "Not found"
uv run wily report src/
```

`wily diff src/` works at directory level because it expands to individual files internally.

#### Gating behaviour

Wily is **informational only** — `wily diff` always exits 0 regardless of regressions.
The Xenon job in CI is the hard gate. Wily is the signal you check manually before
merging to confirm you are not quietly degrading MI on a file that stays within
Xenon's absolute thresholds.

## Cutting a release

1. Update `version` in `pyproject.toml` and `src/apicurio_serdes/_version.py`.
2. Update `CHANGELOG.md` — move items from `Unreleased` to the new version section.
3. Commit: `git commit -m "chore: release vX.Y.Z"`.
4. Push to `main`, then create a GitHub Release with tag `vX.Y.Z`.
5. The publish workflow runs automatically: TestPyPI → smoke test → PyPI.
