# Contributing to apicurio-serdes

Thank you for your interest in contributing! Please read this guide before opening an issue or pull request.

## Ways to contribute

- Report bugs via [GitHub Issues](https://github.com/jcbianic/apicurio-serdes/issues/new?template=bug_report.md)
- Suggest features via [GitHub Issues](https://github.com/jcbianic/apicurio-serdes/issues/new?template=feature_request.md)
- Submit pull requests for bug fixes, new features, or documentation
- Improve examples or translate documentation

## Response time

This is a maintainer-led open-source project. You can expect:

- **Issues**: initial response within a week
- **Pull requests**: initial review within two weeks
- **Security reports**: response within 7 days (see [SECURITY.md](SECURITY.md))

## Development setup

This project uses [uv](https://docs.astral.sh/uv/) for dependency management — a fast, modern replacement for pip/venv. If you are new to it:

```bash
# Install uv (once)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
git clone https://github.com/jcbianic/apicurio-serdes.git
cd apicurio-serdes
uv sync --group dev
```

## Running checks locally

```bash
# Lint and format (ruff via pre-commit)
uv run pre-commit run --all-files

# Type checking (strict mypy)
uv run mypy

# Tests — 100% branch coverage is enforced (see philosophy below)
uv run pytest

# Docs
uv run mkdocs build --strict
```

## Project philosophy

- **100% branch coverage**: Every line and branch in the library must be covered by tests. This is a hard requirement enforced by CI. It ensures that schema caching, wire format switching, and error handling paths are always exercised.
- **Sync and async parity**: The library exposes both `ApicurioRegistryClient` and `AsyncApicurioRegistryClient`. Any behavioral change must apply to both.
- **Minimal dependencies**: Core dependencies are `fastavro` and `httpx` only. New runtime dependencies require strong justification.
- **Stable public API**: Once a version is released, the public surface (`__init__.py` exports) must remain backward-compatible until a major version bump.

## What we welcome

- Bug fixes with a regression test
- Performance improvements to schema caching or (de)serialization
- Documentation improvements and additional examples
- Test coverage for edge cases

## What requires prior discussion

**Open an issue before starting substantial work** to avoid wasted effort:

- New wire formats
- Changes to the schema caching strategy
- New runtime dependencies
- Breaking changes to public APIs
- New serialization formats (e.g., Protobuf)

## Pull request process

1. Fork the repository and create a branch from `main`.
2. Follow [Conventional Commits](https://www.conventionalcommits.org/) for commit messages (`feat:`, `fix:`, `docs:`, `refactor:`).
3. Ensure all checks pass (`pytest`, `mypy`, `pre-commit`, `mkdocs build`).
4. Open a pull request against `main`. All CI checks must be green before merging.

## Reporting bugs

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md). The most useful reports include:

- A **complete, runnable script** that reproduces the problem
- Your Python version, `apicurio-serdes` version, and Apicurio Registry version
- Whether you are using the sync or async client
- The wire format (`CONFLUENT_PAYLOAD` or `KAFKA_HEADERS`)

## Requesting features

Use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md). Describe the use case first — not just the solution.

## Security vulnerabilities

Please **do not** open a public issue. See [SECURITY.md](SECURITY.md).
