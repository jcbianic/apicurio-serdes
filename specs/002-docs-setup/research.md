# Research: Documentation Site

## Decision 1: i18n Approach

**Question**: How to support full English + French documentation with MkDocs Material?

**Options considered**:

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `mkdocs-static-i18n` plugin (single build) | One `mkdocs.yml`, automatic fallback for untranslated pages, simpler CI | Incompatible with Material blog plugin, `mkdocs serve` shows one language at a time |
| B | Separate `mkdocs.yml` per language | Full plugin compatibility, clean search per language, endorsed by Material maintainer | Two config files, no automatic fallback, duplicate nav structure |

**Decision**: **Option A — `mkdocs-static-i18n` plugin with suffix structure**

**Rationale**: The project does not use the Material blog plugin and has no plans to. A single-build approach reduces configuration duplication and provides automatic fallback for pages not yet translated — critical during the initial rollout where French content will be added incrementally. The suffix structure (`index.en.md` / `index.fr.md`) keeps translations adjacent to their English counterparts, making it easy to see which pages need translation.

**Version**: `mkdocs-static-i18n[material]>=1.3.0,<2.0`

---

## Decision 2: File Naming Convention

**Question**: Suffix structure (`page.en.md` / `page.fr.md`) or folder structure (`en/page.md` / `fr/page.md`)?

**Decision**: **Suffix structure**

**Rationale**: Co-locating translations next to each other makes it immediately visible which pages have French translations and which don't. Folder structure separates translations into different directories, making it harder to spot missing translations at a glance. The suffix approach also avoids duplicating the directory hierarchy.

---

## Decision 3: API Reference Language

**Question**: Should the API reference be translated to French?

**Options considered**:

| Option | Approach | Effort | Quality Risk |
|--------|----------|--------|-------------|
| A | English-only API reference | None | None — docstrings are canonical |
| B | French labels via mkdocstrings locale | Low | Medium — FR label coverage in mkdocstrings-python is partial |
| C | Bilingual docstrings | Very high | High — maintenance burden, no tooling support |

**Decision**: **Option A — English-only API reference, shared across both languages**

**Rationale**: mkdocstrings generates reference from Python docstrings, which are written in English. The API reference is a technical document where English is the lingua franca. French labels (e.g., "Paramètres" instead of "Parameters") provide marginal value and risk inconsistency if mkdocstrings-python's FR translation coverage is incomplete. The API reference page will include a brief note in French explaining that the reference is maintained in English as the canonical source.

This satisfies FR-009 with a documented, justified exception: the API reference is auto-generated from source code (FR-005) and is inherently language-neutral (code, types, signatures). Narrative wrapper text on the API reference page will still be translated.

---

## Decision 4: Search Configuration

**Question**: How to support full-text search in both English and French (FR-010)?

**Decision**: Configure the built-in Material search plugin with both `en` and `fr` language stemmers. The `mkdocs-static-i18n` plugin generates separate search indexes per language build.

**Configuration**:
```yaml
plugins:
  - search:
      lang:
        - en
        - fr
      separator: '[\s\u00a0\-,:!=\[\]()"/]+|(?!\b)(?=[A-Z][a-z])|\.(?!\d)|&[lg]t;'
```

The separator includes `\u00a0` (non-breaking space) for French typographic conventions before `:`, `?`, `!`, `;`.

---

## Decision 5: Content Structure (Diátaxis)

**Question**: How to organize the documentation sections?

**Decision**: Follow the [Diátaxis framework](https://diataxis.fr/) already implicit in the existing scaffold:

| Diátaxis quadrant | Section | Spec coverage |
|-------------------|---------|---------------|
| Tutorial | Getting Started (installation + quickstart) | FR-001, FR-002, FR-003 |
| How-to | How-to Guides | FR-007 |
| Explanation | Concepts | FR-006 |
| Reference | API Reference + Migration Guide + Changelog | FR-004, FR-005, FR-008 |

The migration guide sits in Reference because it is a comparative lookup document, not a task-oriented guide.

---

## Decision 6: MkDocs Material Features

**Question**: Which Material features to enable beyond the current configuration?

**Decision**: Add the following features to the existing config:

- `navigation.instant` — SPA-like page transitions (faster navigation)
- `navigation.top` — back-to-top button
- `navigation.indexes` — section index pages
- `toc.integrate` — integrate table of contents into left sidebar
- `navigation.footer` — previous/next page navigation in footer
- `content.tabs.link` — linked content tabs (useful for code examples)

---

## Decision 7: Versioned Documentation

**Question**: Should documentation be versioned per release (edge case from spec)?

**Decision**: Defer versioning to a future feature. The library is pre-1.0 with a single released version. Use `mike` when multiple versions need simultaneous hosting. For now, the site represents the `latest` version and is rebuilt on each release. This satisfies FR-012 (keep in sync with released version) without the complexity of multi-version hosting.

---

## Tessl Tiles

No tiles found for MkDocs, mkdocs-material, mkdocs-static-i18n, or mkdocstrings. Tessl MCP tools unavailable in this session.

### Technologies Without Tiles

- mkdocs: No tile found
- mkdocs-material: No tile found
- mkdocs-static-i18n: No tile found
- mkdocstrings: No tile found
