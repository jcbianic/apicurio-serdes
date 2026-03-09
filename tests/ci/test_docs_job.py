"""YAML validation tests for ci.yml docs job using mkdocs build --strict.

Covers: TS-023, TS-024
"""

from __future__ import annotations

from typing import Any


class TestDocsJob:
    """TS-023, TS-024: Documentation build is validated on every PR."""

    def test_docs_job_exists(self, ci_workflow: dict[str, Any]) -> None:
        assert "docs-build" in ci_workflow["jobs"]

    def test_docs_runs_on_ubuntu(self, ci_workflow: dict[str, Any]) -> None:
        docs = ci_workflow["jobs"]["docs-build"]
        assert docs["runs-on"] == "ubuntu-latest"

    def test_docs_uses_python_313(self, ci_workflow: dict[str, Any]) -> None:
        docs = ci_workflow["jobs"]["docs-build"]
        setup_python_steps = [
            s
            for s in docs["steps"]
            if s.get("uses", "").startswith("actions/setup-python")
        ]
        assert len(setup_python_steps) == 1
        assert setup_python_steps[0]["with"]["python-version"] == "3.13"

    def test_docs_runs_mkdocs_build_strict(self, ci_workflow: dict[str, Any]) -> None:
        docs = ci_workflow["jobs"]["docs-build"]
        run_steps = [s.get("run", "") for s in docs["steps"]]
        assert any("uv run mkdocs build --strict" in step for step in run_steps), (
            "Docs job must run 'uv run mkdocs build --strict'"
        )
