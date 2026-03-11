# ADR-015: No abstraction layer for Apicurio API paths

**Status:** Accepted
**Date:** 2026-03-11
**Context:** PR #32 review item 16 — "Hardcoded Apicurio v3 API paths"

## Context

The review flagged that endpoint strings like
`/groups/{group_id}/artifacts/{artifact_id}/versions/latest/content` are
hardcoded in client methods with no path-building abstraction. If Apicurio
releases a v4 API, every method needs editing.

## Decision

Keep API paths hardcoded. Do not create a path-building abstraction or
API version registry.

## Rationale

- This library explicitly targets Apicurio Registry v3. The package name,
  documentation, and API design are all built around v3 semantics.
- A v4 API would likely change not just paths but semantics (different
  headers, different response formats, different ID types). A path
  abstraction would not absorb those changes — a new client implementation
  would be needed regardless.
- Adding an abstraction layer for one API version is premature. It adds
  indirection with no current benefit and makes the code harder to read
  (paths are now in a separate file instead of next to the HTTP call).
- The paths are already consolidated in `_base.py` (`_schema_endpoint`,
  `_id_endpoint`). If v4 support is ever needed, these two methods are
  the only places to change.

## Consequences

- API paths are readable and grep-able directly in the base class.
- v4 support would require a new client class or base class, not a config
  change. This is acceptable given the scope of v3→v4 changes.
