# ADR-018: Keep CI YAML structure tests

**Status:** Accepted
**Date:** 2026-03-11
**Context:** PR #32 review item 19 — "CI YAML tests are testing structure, not behavior"

## Context

The review flagged that `tests/ci/` parses YAML files and asserts on
keys/values. These tests break on any legitimate CI config change and
provide no guarantee that CI actually works. They are regression tests
for file contents, not functional tests.

## Decision

Keep the CI YAML structure tests.

## Rationale

- These tests serve a different purpose than functional tests: they are
  **configuration drift detectors**. They ensure that CI workflows maintain
  required properties (e.g., coverage thresholds, required jobs, artifact
  signing steps) that are easy to accidentally remove during workflow edits.
- CI workflows are code that runs infrequently and fails silently. A
  removed coverage step won't fail CI — it will just stop measuring
  coverage. The structure tests catch this.
- The tests are cheap to maintain: when a CI change is intentional, the
  test is updated alongside the workflow file. The maintenance cost is
  proportional to the frequency of CI changes (low).
- Functional CI testing (running the workflow in a test environment) is
  orders of magnitude more complex and slow. The structure tests provide
  80% of the value at 1% of the cost.

## Consequences

- Intentional CI changes require updating both the workflow file and the
  corresponding test. This is a feature, not a bug — it forces deliberate
  changes.
