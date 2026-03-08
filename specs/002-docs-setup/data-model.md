# Data Model: Documentation Site — Information Architecture

## Content Entities

### Page

The atomic unit of documentation. Each page has:

| Field | Type | Description |
|-------|------|-------------|
| `path` | string | File path relative to `docs/` (e.g., `concepts/wire-format.en.md`) |
| `title` | string | Page heading displayed in nav and `<title>` |
| `section` | enum | One of: `home`, `getting-started`, `user-guide`, `concepts`, `how-to`, `migration`, `api-reference`, `changelog` |
| `diátaxis_quadrant` | enum | One of: `tutorial`, `how-to`, `explanation`, `reference` |
| `language` | enum | `en` or `fr` |
| `requirements` | list[string] | FR-XXX IDs this page satisfies |
| `stories` | list[string] | User story IDs this page addresses |
| `has_code_examples` | bool | Whether the page contains Python code blocks |

### Translation Pair

A 1:1 relationship between an English page and its French counterpart.

| Field | Type | Description |
|-------|------|-------------|
| `en_path` | string | English page path (e.g., `index.en.md`) |
| `fr_path` | string | French page path (e.g., `index.fr.md`) |
| `status` | enum | `translated`, `pending`, `not_applicable` |

API reference has `status: not_applicable` (shared, auto-generated).

### Section

A navigational grouping of pages.

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Section name in nav (e.g., "Getting Started") |
| `name_fr` | string | French section name (e.g., "Démarrage") |
| `pages` | list[Page] | Ordered list of pages in the section |
| `diátaxis_quadrant` | enum | Primary quadrant for the section |

## Content Inventory

### Home

| Page | EN path | FR path | Quadrant | Requirements |
|------|---------|---------|----------|-------------|
| Homepage | `index.en.md` | `index.fr.md` | tutorial | FR-001 |

### Getting Started

| Page | EN path | FR path | Quadrant | Requirements |
|------|---------|---------|----------|-------------|
| Installation | `getting-started/installation.en.md` | `getting-started/installation.fr.md` | tutorial | FR-002 |
| Quickstart | `getting-started/quickstart.en.md` | `getting-started/quickstart.fr.md` | tutorial | FR-002, FR-003 |

### User Guide

| Page | EN path | FR path | Quadrant | Requirements |
|------|---------|---------|----------|-------------|
| Avro Serializer | `user-guide/avro-serializer.en.md` | `user-guide/avro-serializer.fr.md` | how-to | FR-007 |

### Concepts

| Page | EN path | FR path | Quadrant | Requirements |
|------|---------|---------|----------|-------------|
| Wire Format | `concepts/wire-format.en.md` | `concepts/wire-format.fr.md` | explanation | FR-006a |
| Schema Caching | `concepts/schema-caching.en.md` | `concepts/schema-caching.fr.md` | explanation | FR-006b |
| Addressing Model | `concepts/addressing-model.en.md` | `concepts/addressing-model.fr.md` | explanation | FR-006c |

### How-to Guides

| Page | EN path | FR path | Quadrant | Requirements |
|------|---------|---------|----------|-------------|
| Custom Serialization | `how-to/custom-serialization.en.md` | `how-to/custom-serialization.fr.md` | how-to | FR-007a |
| Identifier Selection | `how-to/identifier-selection.en.md` | `how-to/identifier-selection.fr.md` | how-to | FR-007b |
| Error Handling | `how-to/error-handling.en.md` | `how-to/error-handling.fr.md` | how-to | FR-007c |

### Migration

| Page | EN path | FR path | Quadrant | Requirements |
|------|---------|---------|----------|-------------|
| From confluent-kafka | `migration/from-confluent-kafka.en.md` | `migration/from-confluent-kafka.fr.md` | reference | FR-004 |

### API Reference

| Page | EN path | FR path | Quadrant | Requirements |
|------|---------|---------|----------|-------------|
| API Reference | `api-reference/index.md` | (shared) | reference | FR-005, FR-014 |

### Changelog

| Page | EN path | FR path | Quadrant | Requirements |
|------|---------|---------|----------|-------------|
| Changelog | `changelog.en.md` | `changelog.fr.md` | reference | FR-008 |

## Relationships

```text
Section 1──* Page
Page    1──1 Translation Pair (via suffix convention)
Page    *──* Requirement (FR-XXX)
Page    *──* User Story (US1–US5)
```

## Validation Rules

1. Every EN page must have a corresponding FR page (except API reference)
2. Every FR-XXX requirement must map to at least one page
3. Every page with `has_code_examples: true` must contain only syntactically valid Python (FR-013)
4. The API reference page must reference all public symbols with zero missing-doc warnings (FR-014)
5. Nav structure must be identical in both languages (FR-011)

## State Transitions

Pages follow this lifecycle during implementation:

```
[scaffold] → [english_content] → [french_translation] → [validated]
```

- **scaffold**: File created with stub content
- **english_content**: Full English content written and reviewed
- **french_translation**: French translation complete
- **validated**: Build passes `mkdocs build --strict`, content reviewed
