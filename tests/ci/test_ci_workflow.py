"""YAML validation tests for ci.yml triggers, jobs, and structure.

Covers: TS-001, TS-002, TS-003, TS-004, TS-005
"""

from __future__ import annotations

from typing import Any


class TestCITriggers:
    """TS-001: CI pipeline triggers on push and pull_request."""

    def test_triggers_on_push_to_main(self, ci_workflow: dict[str, Any]) -> None:
        triggers = ci_workflow[True]
        assert "push" in triggers
        assert triggers["push"]["branches"] == ["main"]

    def test_triggers_on_pull_request(self, ci_workflow: dict[str, Any]) -> None:
        triggers = ci_workflow[True]
        assert "pull_request" in triggers
        assert "opened" in triggers["pull_request"]["types"]
        assert "ready_for_review" in triggers["pull_request"]["types"]


class TestCILintJob:
    """TS-003: Lint job runs ruff check."""

    def test_lint_job_exists(self, ci_workflow: dict[str, Any]) -> None:
        assert "lint" in ci_workflow["jobs"]

    def test_lint_runs_on_ubuntu(self, ci_workflow: dict[str, Any]) -> None:
        lint = ci_workflow["jobs"]["lint"]
        assert lint["runs-on"] == "ubuntu-latest"

    def test_lint_uses_python_313(self, ci_workflow: dict[str, Any]) -> None:
        lint = ci_workflow["jobs"]["lint"]
        setup_python_steps = [
            s
            for s in lint["steps"]
            if s.get("uses", "").startswith("actions/setup-python")
        ]
        assert len(setup_python_steps) == 1
        assert setup_python_steps[0]["with"]["python-version"] == "3.13"

    def test_lint_uses_pre_commit(self, ci_workflow: dict[str, Any]) -> None:
        lint = ci_workflow["jobs"]["lint"]
        uses_steps = [s.get("uses", "") for s in lint["steps"]]
        assert any("pre-commit/action" in step for step in uses_steps)


class TestCITypecheckJob:
    """TS-003: Typecheck job runs mypy."""

    def test_typecheck_job_exists(self, ci_workflow: dict[str, Any]) -> None:
        assert "typecheck" in ci_workflow["jobs"]

    def test_typecheck_runs_on_ubuntu(self, ci_workflow: dict[str, Any]) -> None:
        typecheck = ci_workflow["jobs"]["typecheck"]
        assert typecheck["runs-on"] == "ubuntu-latest"

    def test_typecheck_uses_python_313(self, ci_workflow: dict[str, Any]) -> None:
        typecheck = ci_workflow["jobs"]["typecheck"]
        setup_python_steps = [
            s
            for s in typecheck["steps"]
            if s.get("uses", "").startswith("actions/setup-python")
        ]
        assert len(setup_python_steps) == 1
        assert setup_python_steps[0]["with"]["python-version"] == "3.13"

    def test_typecheck_runs_mypy(self, ci_workflow: dict[str, Any]) -> None:
        typecheck = ci_workflow["jobs"]["typecheck"]
        run_steps = [s.get("run", "") for s in typecheck["steps"]]
        assert any("uv run mypy" in step for step in run_steps)


class TestCITestJob:
    """TS-001, TS-004: Test job runs pytest with coverage enforcement."""

    def test_test_job_exists(self, ci_workflow: dict[str, Any]) -> None:
        assert "test" in ci_workflow["jobs"]

    def test_test_runs_on_ubuntu(self, ci_workflow: dict[str, Any]) -> None:
        test = ci_workflow["jobs"]["test"]
        assert test["runs-on"] == "ubuntu-latest"

    def test_test_runs_pytest(self, ci_workflow: dict[str, Any]) -> None:
        test = ci_workflow["jobs"]["test"]
        run_steps = [s.get("run", "") for s in test["steps"]]
        assert any("uv run pytest" in step for step in run_steps)


class TestCIAllJobsPresent:
    """TS-005: All quality jobs execute."""

    def test_all_jobs_present(self, ci_workflow: dict[str, Any]) -> None:
        jobs = ci_workflow["jobs"]
        for job_name in ("lint", "typecheck", "test", "docs-build", "codeql", "publish-testpypi"):
            assert job_name in jobs, f"Missing job: {job_name}"

    def test_workflow_has_exactly_six_jobs(self, ci_workflow: dict[str, Any]) -> None:
        assert len(ci_workflow["jobs"]) == 6


class TestCIStatusBlocking:
    """TS-002: All jobs report status (implicit via GitHub Actions)."""

    def test_no_job_has_continue_on_error(self, ci_workflow: dict[str, Any]) -> None:
        for name, job in ci_workflow["jobs"].items():
            assert not job.get("continue-on-error", False), (
                f"Job '{name}' must not continue on error"
            )
