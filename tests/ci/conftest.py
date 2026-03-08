"""Shared fixtures for CI/CD YAML validation tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


def _load_workflow(name: str) -> dict[str, Any]:
    """Load and parse a GitHub Actions workflow YAML file.

    Note: YAML 1.1 parses the ``on`` key as boolean ``True``.
    Access trigger configuration via ``workflow[True]``.
    """
    path = WORKFLOWS_DIR / name
    with path.open() as f:
        return yaml.safe_load(f)


@pytest.fixture()
def ci_workflow() -> dict[str, Any]:
    """Load ci.yml workflow definition."""
    return _load_workflow("ci.yml")


@pytest.fixture()
def publish_workflow() -> dict[str, Any]:
    """Load publish.yml workflow definition."""
    return _load_workflow("publish.yml")


@pytest.fixture()
def security_workflow() -> dict[str, Any]:
    """Load security.yml workflow definition."""
    return _load_workflow("security.yml")


@pytest.fixture()
def dependabot_config() -> dict[str, Any]:
    """Load dependabot.yml configuration."""
    path = REPO_ROOT / ".github" / "dependabot.yml"
    with path.open() as f:
        return yaml.safe_load(f)


@pytest.fixture()
def readme_content() -> str:
    """Load README.md content."""
    path = REPO_ROOT / "README.md"
    return path.read_text()
