# Contributing to apicurio-serdes

Thank you for your interest in contributing! This guide explains how to get started.

## Ways to contribute

- Report bugs via [GitHub Issues](https://github.com/jcbianic/apicurio-serdes/issues)
- Suggest features or improvements
- Submit pull requests for bug fixes or new features
- Improve documentation

## Development setup

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
git clone https://github.com/jcbianic/apicurio-serdes.git
cd apicurio-serdes
uv sync --group dev
```

## Running checks locally

```bash
# Lint and format
uv run pre-commit run --all-files

# Type checking
uv run mypy

# Tests (100% coverage required)
uv run pytest

# Docs
uv run mkdocs build --strict
```

## Pull request process

1. Fork the repository and create a branch from `main`.
2. Make your changes — all tests must pass and coverage must stay at 100%.
3. Follow [Conventional Commits](https://www.conventionalcommits.org/) for commit messages (e.g. `feat:`, `fix:`, `docs:`).
4. Open a pull request against `main`. CI must be green before merging.

## Reporting bugs

Please use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md) and include:

- A clear description of the problem
- A minimal reproducer (code snippet or steps)
- Your Python version and `apicurio-serdes` version
- The Apicurio Registry version you are connecting to

## Suggesting features

Open a [feature request](.github/ISSUE_TEMPLATE/feature_request.md) describing the use case and the behaviour you'd like to see.

## Security vulnerabilities

Please **do not** open a public issue. Report them via [GitHub Security Advisories](https://github.com/jcbianic/apicurio-serdes/security/advisories/new). See [SECURITY.md](SECURITY.md) for details.
