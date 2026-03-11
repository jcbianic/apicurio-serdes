# ADR-019: Accept GIL dependency for thread safety tests

**Status:** Accepted
**Date:** 2026-03-11
**Context:** PR #32 review item 21 — "Thread safety tests rely on the GIL"

## Context

The review flagged that concurrent tests use `ThreadPoolExecutor` and
`asyncio.gather`, but correctness depends on CPython's GIL making dict
operations atomic. With free-threaded Python (PEP 703 / 3.13t), these
tests may start failing or pass non-deterministically while masking real
races.

## Decision

Accept the GIL dependency. Do not rewrite thread safety tests for
free-threaded Python compatibility.

## Rationale

- Free-threaded Python (3.13t) is experimental and not a supported target
  for this library yet. Investing in no-GIL-safe test infrastructure now
  is premature.
- The thread safety guarantees in the library itself (double-checked locking
  in the registry client) use explicit locks and are already correct under
  both GIL and no-GIL. The tests verify the lock behavior works.
- The specific race condition (duplicate `fastavro.parse_schema` calls in
  the deserializer's `_parsed_cache`) is a benign race under the GIL
  (see ADR-009). When free-threaded Python is targeted, both the
  production code and the tests will need updating together.
- Writing deterministic concurrency tests is hard and often produces
  flaky tests. The current approach (concurrent execution + assertion on
  HTTP call count) validates the deduplication property effectively under
  the GIL.

## Revisit Trigger

- When targeting free-threaded Python, audit all dict-based caches and
  their tests. Use `threading.Lock` or `concurrent.futures` patterns
  that are correct without the GIL. Consider `pytest-threadrace` or
  similar tools for race detection.
