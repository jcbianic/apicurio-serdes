# Quickstart: Contributing to Documentation

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager

## Setup

```bash
# Install doc dependencies
uv sync --group docs

# Serve locally (English)
uv run mkdocs serve

# Build for both languages
uv run mkdocs build --strict
```

## File Naming Convention

All content files use the suffix convention for i18n:

| Language | File | Example |
|----------|------|---------|
| English | `page.en.md` | `docs/index.en.md` |
| French | `page.fr.md` | `docs/index.fr.md` |

Exception: `api-reference/index.md` has no suffix (shared, auto-generated).

## Adding a New Page

1. Create `docs/section/page.en.md` with English content
2. Create `docs/section/page.fr.md` with French translation
3. Add the page to `nav:` in `mkdocs.yml` (use path without suffix: `section/page.md`)
4. Run `uv run mkdocs build --strict` to validate

## Writing Code Examples

All code examples must be syntactically valid Python consistent with the current API:

```python
from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroSerializer
from apicurio_serdes.serialization import SerializationContext, MessageField

client = ApicurioRegistryClient(url="http://localhost:8080", group_id="my-group")
serializer = AvroSerializer(registry_client=client, artifact_id="my-schema")

ctx = SerializationContext(topic="my-topic", field=MessageField.VALUE)
payload = serializer({"name": "Alice", "age": 30}, ctx)
```

## Translation Guidelines

- Translate all narrative text, headings, and admonitions
- Keep code examples identical in both languages (Python is universal)
- Keep technical terms in English when they are the canonical name (e.g., `group_id`, `AvroSerializer`, `wire format`)
- Translate UI labels, descriptions, and explanations
- Use natural French — avoid literal translations that read awkwardly

## Validation

```bash
# Full build with strict mode (zero warnings required)
uv run mkdocs build --strict

# Check that the API reference has no missing symbols
# (mkdocstrings will warn on missing docstrings in strict mode)
```

## Directory Layout

```
docs/
├── index.en.md / index.fr.md
├── changelog.en.md / changelog.fr.md
├── getting-started/
│   ├── installation.en.md / installation.fr.md
│   └── quickstart.en.md / quickstart.fr.md
├── user-guide/
│   └── avro-serializer.en.md / avro-serializer.fr.md
├── concepts/
│   ├── wire-format.en.md / wire-format.fr.md
│   ├── schema-caching.en.md / schema-caching.fr.md
│   └── addressing-model.en.md / addressing-model.fr.md
├── how-to/
│   ├── custom-serialization.en.md / custom-serialization.fr.md
│   ├── identifier-selection.en.md / identifier-selection.fr.md
│   └── error-handling.en.md / error-handling.fr.md
├── migration/
│   └── from-confluent-kafka.en.md / from-confluent-kafka.fr.md
└── api-reference/
    └── index.md (shared, auto-generated)
```
