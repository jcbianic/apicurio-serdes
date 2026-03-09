"""YAML validation tests for security.yml workflow.

Covers: TS-018, TS-019, TS-020, TS-021, TS-022
"""

from __future__ import annotations

from typing import Any


class TestSecurityTriggers:
    """TS-021, TS-022: Security workflow triggers on push, PRs, and weekly schedule."""

    def test_triggers_on_push_to_main(self, security_workflow: dict[str, Any]) -> None:
        triggers = security_workflow[True]
        assert "push" in triggers
        assert triggers["push"]["branches"] == ["main"]

    def test_triggers_on_pull_request_to_main(
        self, security_workflow: dict[str, Any]
    ) -> None:
        triggers = security_workflow[True]
        assert "pull_request" in triggers
        assert triggers["pull_request"]["branches"] == ["main"]

    def test_triggers_on_weekly_schedule(
        self, security_workflow: dict[str, Any]
    ) -> None:
        triggers = security_workflow[True]
        assert "schedule" in triggers
        crons = [entry["cron"] for entry in triggers["schedule"]]
        assert any("0 6 * * 1" in cron for cron in crons), (
            "Must schedule Monday 06:00 UTC"
        )


class TestDependencyAuditJob:
    """TS-018, TS-019: Dependency audit using pip-audit."""

    def test_dependency_audit_job_exists(
        self, security_workflow: dict[str, Any]
    ) -> None:
        assert "dependency-audit" in security_workflow["jobs"]

    def test_dependency_audit_runs_pip_audit(
        self, security_workflow: dict[str, Any]
    ) -> None:
        job = security_workflow["jobs"]["dependency-audit"]
        run_steps = [s.get("run", "") for s in job["steps"]]
        assert any("pip-audit" in step for step in run_steps)

    def test_dependency_audit_runs_on_ubuntu(
        self, security_workflow: dict[str, Any]
    ) -> None:
        job = security_workflow["jobs"]["dependency-audit"]
        assert job["runs-on"] == "ubuntu-latest"


class TestCodeQLJob:
    """TS-020: CodeQL static security analysis."""

    def test_codeql_job_exists(self, security_workflow: dict[str, Any]) -> None:
        assert "codeql" in security_workflow["jobs"]

    def test_codeql_has_security_events_write(
        self, security_workflow: dict[str, Any]
    ) -> None:
        job = security_workflow["jobs"]["codeql"]
        perms = job.get("permissions", {})
        assert perms.get("security-events") == "write"

    def test_codeql_uses_init_and_analyze(
        self, security_workflow: dict[str, Any]
    ) -> None:
        job = security_workflow["jobs"]["codeql"]
        uses = [s.get("uses", "") for s in job["steps"]]
        assert any("codeql-action/init" in u for u in uses), "Must use codeql init"
        assert any("codeql-action/analyze" in u for u in uses), (
            "Must use codeql analyze"
        )

    def test_codeql_configures_python_language(
        self, security_workflow: dict[str, Any]
    ) -> None:
        job = security_workflow["jobs"]["codeql"]
        init_steps = [
            s for s in job["steps"] if "codeql-action/init" in s.get("uses", "")
        ]
        assert len(init_steps) >= 1
        languages = init_steps[0].get("with", {}).get("languages", "")
        assert "python" in languages
