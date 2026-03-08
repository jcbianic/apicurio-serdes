# Feature Specification: Documentation Site

**Feature Branch**: `007-docs-setup`
**Created**: 2026-03-08
**Status**: Draft
**Input**: User description: "for setting up a mkdocs documentation, very complete, very user-friendly, translated at least in french and english, pedagogic, and crystal clear about what we are trying to solve."

## User Stories *(mandatory)*

### User Story 1 - New visitor understands the problem and gets started (Priority: P1)

As a Python data engineer who discovers `apicurio-serdes` for the first time, I want to immediately understand what problem this library solves and get my first Kafka message serialized end-to-end in a single reading, so that I can evaluate the library and start using it without consulting external resources.

**Why this priority**: Documentation that fails to communicate the problem and enable a fast first success delivers no value. The homepage and quickstart are the primary entry point — if they do not work, no other section matters.

**Independent Test**: Can be fully tested by a developer unfamiliar with the library following only the homepage and quickstart guide, with no prior knowledge of Apicurio Registry, and producing valid Confluent-framed Avro bytes without consulting any other resource.

**Acceptance Scenarios**:

1. **Given** a developer who has never seen the library arrives at the documentation homepage, **When** they read the homepage, **Then** they can articulate in one sentence what problem `apicurio-serdes` solves, who it is for, and what makes it different from existing approaches.

2. **Given** a developer following the quickstart guide from the first line, **When** they complete every step in sequence, **Then** they have a working Python script that successfully serializes a Python dict to Confluent-framed Avro bytes using their Apicurio Registry instance (or a documented local alternative).

3. **Given** a developer following the quickstart who encounters one of the three most common setup errors (wrong registry URL, non-existent artifact, invalid data), **When** they consult the troubleshooting section, **Then** they find a description of the error, its root cause, and a corrective action without leaving the quickstart page.

---

### User Story 2 - Confluent-kafka migrant identifies all differences and adapts their code (Priority: P2)

As a Python developer currently using `confluent-kafka`'s schema registry serializers, I want a migration guide that puts the two APIs side by side with a complete map of differences, so that I can update my existing producer code and know exactly what will change in behavior without surprises.

**Why this priority**: Lowering switching cost from `confluent-kafka` is the core value proposition of this library (per PREMISE). A migration guide directly addresses the primary adoption barrier.

**Independent Test**: Can be fully tested by a developer already familiar with `confluent-kafka` reading only the migration guide and adapting a sample producer to `apicurio-serdes`, without consulting any other section of the documentation.

**Acceptance Scenarios**:

1. **Given** a developer using `confluent-kafka`'s `AvroSerializer`, **When** they read the migration guide, **Then** they can enumerate every class name, parameter name, and behavioral difference between the two libraries from a single reading — including the required `group_id` parameter that has no direct counterpart in Confluent's client.

2. **Given** a developer who has read the migration guide, **When** they update their existing producer code, **Then** they need to touch no more than the import lines and the client configuration to achieve a working migration for the common case.

3. **Given** a developer whose schemas are organized under a non-default group, **When** they read the migration guide, **Then** they understand what `group_id` represents in Apicurio, why it is required, and how to map their existing schema naming to Apicurio's group/artifact model.

---

### User Story 3 - Developer finds the exact API details they need (Priority: P3)

As a developer integrating `apicurio-serdes` in a production system, I want a complete API reference listing every public class, method, parameter, return value, and exception, so that I can look up any detail without reading source code.

**Why this priority**: A library without a complete API reference forces users to guess or read internals. The constitution mandates a reference auto-generated from docstrings — this story delivers that mandate.

**Independent Test**: Can be fully tested by verifying that every public symbol in the library appears in the API reference with description, parameters, return type, raised exceptions, and a usage example.

**Acceptance Scenarios**:

1. **Given** the API reference, **When** a developer looks up `AvroSerializer`, **Then** they find its constructor signature, every optional parameter with its default value, a short description of what the class does, and a minimal usage example.

2. **Given** the API reference, **When** a developer looks up any public class or method, **Then** they find: a description, all parameters (name, type, default if applicable, description), return type and description, and all exceptions that may be raised with an explanation of when each is raised.

3. **Given** a developer who encounters a `SchemaNotFoundError` at runtime, **When** they look it up in the API reference, **Then** they understand what triggered it, which attributes it carries (group_id, artifact_id), and how to handle it in their code.

---

### User Story 4 - French-speaking developer reads the complete documentation in French (Priority: P4)

As a French-speaking data engineer at a European organization using Apicurio Registry, I want to read the entire documentation in French — including the homepage, quickstart, user guide, conceptual explanations, and migration guide — so that I can understand and use the library fully without a language barrier.

**Why this priority**: A significant portion of the Red Hat / OpenShift user base is French-speaking. Providing documentation in both languages is explicitly required and is part of what "user-friendly" means for this library's target audience.

**Independent Test**: Can be fully tested by a French speaker following only the French version of the documentation from start to finish, performing the same tasks as User Story 1 entirely in French, with no section missing or reverting to English.

**Acceptance Scenarios**:

1. **Given** a French-speaking developer arrives at the documentation site, **When** they switch the interface to French, **Then** all navigation labels, headings, and narrative content appear in correct, natural French.

2. **Given** the French documentation, **When** a developer reads the homepage, quickstart, user guide, conceptual pages, and migration guide in French, **Then** every section present in the English version is also present in French with equivalent depth and no untranslated fragments.

3. **Given** a developer browsing in French who follows the quickstart end-to-end, **When** they complete every step, **Then** the guide is complete and fully functional without needing to switch to English at any point.

---

### User Story 5 - Developer understands key concepts through dedicated conceptual pages (Priority: P5)

As a data engineer new to Apicurio Registry and the Confluent wire format, I want dedicated conceptual explanation pages covering the wire format byte layout, schema caching behaviour, and Apicurio's group/artifact/version addressing model, so that I understand not just how to call the API but why the library works the way it does.

**Why this priority**: Understanding the reasoning behind design decisions builds trust, prevents misuse in edge cases, and is central to the "pedagogic" and "crystal clear" requirements.

**Independent Test**: Can be fully tested by a developer with no prior Apicurio knowledge reading the conceptual pages and then correctly answering: what is the magic byte for, when does the schema cache expire, and how does `group_id` differ from Confluent's addressing model.

**Acceptance Scenarios**:

1. **Given** a conceptual page on the Confluent wire format, **When** a developer reads it, **Then** they understand the byte layout of a serialized message (magic byte, 4-byte schema identifier, Avro payload), the purpose of each field, and the difference between `globalId` and `contentId` identifiers.

2. **Given** a conceptual page on schema caching, **When** a developer reads it, **Then** they understand when the cache is populated, how long it persists, when to create a new client instance, and what thread-safety guarantees the cache provides.

3. **Given** a conceptual page on Apicurio's addressing model, **When** a developer reads it, **Then** they understand the group → artifact → version hierarchy, why `group_id` is required in `apicurio-serdes`, and how to map an existing Confluent schema naming convention to Apicurio's model.

---

### Edge Cases

- What happens when a documentation page references a public symbol that was removed or renamed in a subsequent release?
- How does the site present content when a user's selected language has a section that is not yet translated?
- What is the process for detecting and correcting documentation errors when code examples go out of date?
- How does versioned documentation work — does each release get its own documentation snapshot, or is there a single "latest" site?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The documentation homepage MUST contain a clear problem statement that explains what `apicurio-serdes` solves, who it is for, and what distinguishes it from existing alternatives — readable in under 2 minutes without navigating elsewhere.

- **FR-002**: The documentation MUST include a quickstart guide that takes a developer from zero to a working serialization example in a single reading, requiring no prior knowledge of Apicurio Registry.

- **FR-003**: The quickstart guide MUST include a troubleshooting section addressing the three most common setup errors: incorrect registry URL, missing or misnamed artifact, and invalid input data.

- **FR-004**: The documentation MUST include a migration guide that maps the `confluent-kafka` schema registry API to `apicurio-serdes`, covering: class names, constructor parameters, invocation patterns, and all behavioral differences including the `group_id` requirement.

- **FR-005**: The documentation MUST include an API reference that is auto-generated from the library's inline docstrings and covers every public symbol with: description, all parameters (name, type, default, description), return type and description, all raiseable exceptions with descriptions, and at least one usage example per class.

- **FR-006**: The documentation MUST include conceptual explanation pages covering: (a) the Confluent wire format byte layout and identifier choices, (b) schema caching behaviour, lifetime, and thread-safety guarantees, (c) Apicurio's group/artifact/version addressing model and how it differs from Confluent's approach.

- **FR-007**: The documentation MUST include how-to guides covering: (a) serializing custom domain objects using the `to_dict` hook, (b) choosing between `globalId` and `contentId` wire format identifiers, (c) handling the three error types raised by the library (`SchemaNotFoundError`, `RegistryConnectionError`, `SerializationError`).

- **FR-008**: The documentation MUST include a changelog that records all user-visible changes, updated on every library release.

- **FR-009**: Every narrative documentation section — homepage, quickstart, user guide, conceptual pages, migration guide, and how-to guides — MUST be available in both English and French with equivalent depth.

- **FR-010**: The documentation site MUST support full-text search in both English and French.

- **FR-011**: Navigation menus, section titles, and all structural labels MUST appear in the user's selected language.

- **FR-012**: The documentation MUST be published as a hosted site and kept in sync with the current released version of the library.

- **FR-013**: All code examples in the documentation MUST be syntactically valid Python and consistent with the current public API of the library.

- **FR-014**: The API reference MUST build with zero missing-documentation warnings.

### Key Entities *(information architecture)*

- **Homepage**: Entry point. Communicates the problem, the target audience, and the value proposition. Contains a short feature overview and links to the quickstart.

- **Quickstart Guide**: Task-oriented page for first-time users. Covers installation, a minimal working example, and troubleshooting for common setup errors.

- **Migration Guide**: Comparative guide for developers moving from `confluent-kafka`. Side-by-side API mapping and exhaustive list of behavioral differences.

- **How-to Guides**: Task-oriented pages, each answering one specific practical question beyond the quickstart.

- **Conceptual Explanations**: Concept-first pages that explain why the library behaves as it does. Covers wire format, schema caching, and schema addressing.

- **API Reference**: Auto-generated reference for all public symbols. Canonical source of truth for the library's public interface.

- **Changelog**: Chronological record of all user-visible changes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer unfamiliar with the library can read the homepage and articulate in one sentence what problem `apicurio-serdes` solves — verifiable by testing with at least 3 developers who have not seen the library before.

- **SC-002**: A developer following only the quickstart guide from start to finish can produce valid Confluent-framed Avro bytes in under 5 minutes of active reading time.

- **SC-003**: A developer familiar with `confluent-kafka`'s schema registry serializers can identify all API and behavioral differences after reading the migration guide alone, with 100% of known differences covered in the guide.

- **SC-004**: The API reference builds with zero missing-documentation warnings and covers 100% of public symbols.

- **SC-005**: Every narrative section available in English is also available in French — the English and French page trees are structurally identical with no untranslated sections.

- **SC-006**: The documentation site search returns at least one relevant result for each of the top 10 most common user search terms (e.g., "serializer", "group_id", "wire format", "caching", "migration", "error") in both English and French.
