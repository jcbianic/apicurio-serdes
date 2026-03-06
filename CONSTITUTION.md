# apicurio-serdes Constitution

<!--
  sync-impact-report:
    version-change: N/A → 1.0.0
    modified-principles: (none — initial ratification)
    added-sections: Core Principles, Quality Standards, Development Workflow, Governance
    removed-sections: (none)
    follow-up-TODOs:
      - Validate coverage-enforcement tooling in CI
      - Confirm wire format defaults against Apicurio 3.x reference implementation
-->

## Core Principles

### I. API Compatibility First

The public interface must remain intentionally compatible with the established
schema-registry API conventions used by the target user base. Users already
familiar with those conventions must be able to apply the same mental model
with minimal friction.

**Rules:**
- Class names, method signatures, and configuration patterns must mirror
  established conventions where a direct analogue exists.
- Deviations must be explicitly justified and documented.
- Backward compatibility of the public API must be preserved across minor
  versions; breaking changes require a MAJOR version bump.

**Rationale:** The primary adoption barrier is switching cost from an
established ecosystem. Lowering that cost is a core value proposition of
this library.

### II. No Schema Representation Opinion

The library must work with plain data structures and raw schema strings.
It must not require any particular schema definition library, data modeling
tool, or serialization framework as a dependency.

**Rules:**
- Public APIs accept plain data structures and raw schema strings as
  first-class inputs.
- Optional transformation hooks (e.g., `to_dict`, `from_dict`) may be
  provided but must default to identity functions.
- No external schema-definition library may appear in the core dependency
  set.

**Rationale:** Coupling the library to a specific schema representation
would exclude large portions of the target user base who have their own
data modeling preferences.

### III. Test-First Development (NON-NEGOTIABLE)

Test-first development MUST be applied for all production code. No
implementation may be written without a preceding failing test that
specifies the intended behaviour. The Red-Green-Refactor cycle is mandatory.

**Rules:**
- No production code may be written without a corresponding failing test
  already in place and reviewed.
- Tests must cover specified behaviour, not implementation details.
- 100% line and branch coverage is required before any feature is
  considered complete.
- Test assertions may not be modified to make failing tests pass — only
  production code may change.

**Rationale:** A library consumed by external teams must be provably
correct, not assumed correct. Test-first development surfaces integration
issues early and keeps the public API honest.

### IV. Wire Format Fidelity

The library must correctly implement every wire format framing convention
it claims to support. Byte-level correctness is non-negotiable.

**Rules:**
- Wire format encoding and decoding must be verified with byte-level tests
  against known reference messages.
- Any supported wire format variant must be selectable at the client level,
  not buried in internals.
- Wire format defaults must match the documented behaviour of the target
  schema registry's native serializers.

**Rationale:** Producers and consumers in an event-streaming cluster must
agree on framing. An incorrect implementation silently corrupts data
pipelines with no observable error at write time.

### V. Simplicity and Minimal Footprint

The library must do one thing well: serialize and deserialize messages
using schemas stored in a schema registry. It must resist scope creep
beyond that responsibility.

**Rules:**
- Registry management operations (creating, updating, deleting artifacts)
  are permanently out of scope and must never be added to the core library.
- Code generation from schemas is permanently out of scope.
- Every public API addition must be justified by a documented user need
  from the target persona.
- Each new runtime dependency requires explicit written justification.

**Rationale:** A focused, minimal library is easier to audit, maintain,
and trust. Users should be able to read and understand the full library
in a single session.

## Quality Standards

- All public symbols must carry static type annotations.
- All public APIs must have docstrings describing parameters, return values,
  and raised exceptions.
- 100% line and branch coverage is a hard quality gate enforced by CI.
- No release may ship with known correctness bugs in the core
  serialization/deserialization path.
- All releases must be published to the public package registry with a
  corresponding signed tag.
- Documentation is a first-class deliverable, not an afterthought:
  - API reference must be auto-generated from docstrings and published
    alongside each release.
  - A narrative user guide (installation, quickstart, how-to guides, and
    conceptual explanations) must be maintained and kept current.
  - A changelog must be maintained and updated on every release, recording
    all user-visible changes.
  - Documentation must be published as a hosted site and kept in sync with
    the released version.

## Development Workflow

- Features follow the IIKit phase discipline: specify → plan → testify →
  tasks → implement. Phases must not be skipped.
- The TDD determination for this project is: **MANDATORY** (per Principle III).
  Run `/iikit-04-testify` before `/iikit-05-tasks` on every feature.
- Every PR must reference the task(s) it addresses.
- All changes to the public API require an explicit backward-compatibility
  assessment documented in the PR description.

## Governance

This constitution supersedes all other guidance when conflicts arise. It
applies to all contributors and all code within this repository.

**Amendment procedure:**
1. Propose the amendment in a PR with rationale and affected principles listed.
2. Increment the version: MAJOR for principle removal or redefinition; MINOR
   for a new principle; PATCH for clarifications or wording only.
3. Update `LAST_AMENDED_DATE` to the merge date.
4. Amendments are recorded in PR descriptions; no separate changelog required.

**Compliance:** All PRs and code reviews must verify compliance with this
constitution. Violations must be flagged before merge.

**Version**: 1.2.0 | **Ratified**: 2026-03-06 | **Last Amended**: 2026-03-06

## Clarifications

### Session 2026-03-06

- Q: What coverage metric is the hard quality gate? -> A: 100% line and branch
  coverage (coverage.py --branch). [Principle III, Quality Standards]
- Q: What documentation standard is constitutionally mandated? -> A: D — auto-generated
  API reference + narrative user guide + changelog + hosted site, published on every
  release and kept in sync with the released version. [Quality Standards]
