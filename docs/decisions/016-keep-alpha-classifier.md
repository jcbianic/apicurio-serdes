# ADR-016: Keep "Development Status :: 3 - Alpha" classifier

**Status:** Accepted
**Date:** 2026-03-11
**Context:** PR #32 review item 17 — "Alpha contradicts the quality posture"

## Context

The review flagged that 100% branch coverage, Sigstore signing, OSSF
Scorecard, SonarCloud, and strict mypy contradict the "Alpha" classifier.
The mixed signal erodes user confidence.

## Decision

Keep the Alpha classifier for now.

## Rationale

- The quality infrastructure reflects engineering standards, not API
  stability. Alpha means "the public API may change without notice" — which
  is true. The library is still pre-1.0 and API surface is still being
  validated by early adopters.
- Promoting to Beta or Stable prematurely creates an implicit contract that
  the API is frozen. The library is not ready for that commitment — several
  open design questions remain (e.g., accepting user-provided httpx clients,
  additional wire formats, JSON/Protobuf support).
- The classifier is a PyPI convention, not a quality statement. High
  test coverage and an Alpha classifier are not contradictory — they mean
  "well-tested but still evolving."

## Revisit Trigger

- Promote to "4 - Beta" after the 1.0 release, when the public API is
  considered stable. Promote to "5 - Production/Stable" after real-world
  production usage validates the API design.
