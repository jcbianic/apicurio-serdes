"""YAML validation tests for ci.yml test matrix covering Python 3.10-3.13.

Covers: TS-025, TS-026
"""

from __future__ import annotations

from typing import Any

EXPECTED_PYTHON_VERSIONS = ["3.10", "3.11", "3.12", "3.13"]


class TestPythonMatrix:
    """TS-025, TS-026: Tests execute on all declared Python versions."""

    def test_test_job_has_matrix_strategy(
        self, ci_workflow: dict[str, Any]
    ) -> None:
        test_job = ci_workflow["jobs"]["test"]
        assert "strategy" in test_job, "Test job must define a strategy"
        assert "matrix" in test_job["strategy"], "Strategy must include a matrix"

    def test_matrix_includes_all_supported_python_versions(
        self, ci_workflow: dict[str, Any]
    ) -> None:
        matrix = ci_workflow["jobs"]["test"]["strategy"]["matrix"]
        assert "python-version" in matrix, "Matrix must include python-version"
        versions = [str(v) for v in matrix["python-version"]]
        for expected in EXPECTED_PYTHON_VERSIONS:
            assert expected in versions, (
                f"Python {expected} missing from matrix; got {versions}"
            )

    def test_matrix_uses_python_version_in_setup(
        self, ci_workflow: dict[str, Any]
    ) -> None:
        test_job = ci_workflow["jobs"]["test"]
        setup_python_steps = [
            s
            for s in test_job["steps"]
            if s.get("uses", "").startswith("actions/setup-python")
        ]
        assert len(setup_python_steps) == 1
        python_version = setup_python_steps[0]["with"]["python-version"]
        assert "${{ matrix.python-version }}" in str(python_version)

    def test_matrix_version_specific_reporting(
        self, ci_workflow: dict[str, Any]
    ) -> None:
        """TS-026: Each matrix entry runs as a separate job for clear attribution."""
        test_job = ci_workflow["jobs"]["test"]
        strategy = test_job["strategy"]
        assert strategy.get("fail-fast") is False, (
            "fail-fast must be false for clear per-version attribution"
        )
