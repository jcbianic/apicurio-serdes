"""YAML validation tests for ci.yml coverage artifact upload configuration.

Covers: TS-006
"""

from __future__ import annotations

from typing import Any


class TestCoverageArtifactUpload:
    """TS-006: Coverage XML report is available as a downloadable build artifact."""

    def test_test_job_has_upload_artifact_step(
        self, ci_workflow: dict[str, Any]
    ) -> None:
        test_job = ci_workflow["jobs"]["test"]
        upload_steps = [
            s
            for s in test_job["steps"]
            if s.get("uses", "").startswith("actions/upload-artifact")
        ]
        assert len(upload_steps) >= 1, "Test job must have an upload-artifact step"

    def test_upload_artifact_includes_coverage_xml(
        self, ci_workflow: dict[str, Any]
    ) -> None:
        test_job = ci_workflow["jobs"]["test"]
        upload_steps = [
            s
            for s in test_job["steps"]
            if s.get("uses", "").startswith("actions/upload-artifact")
        ]
        coverage_uploads = [
            s
            for s in upload_steps
            if "coverage" in s.get("with", {}).get("name", "").lower()
        ]
        assert (
            len(coverage_uploads) >= 1
        ), "Must upload a coverage artifact with 'coverage' in the name"

    def test_coverage_artifact_name_includes_python_version(
        self, ci_workflow: dict[str, Any]
    ) -> None:
        test_job = ci_workflow["jobs"]["test"]
        upload_steps = [
            s
            for s in test_job["steps"]
            if s.get("uses", "").startswith("actions/upload-artifact")
        ]
        coverage_uploads = [
            s
            for s in upload_steps
            if "coverage" in s.get("with", {}).get("name", "").lower()
        ]
        assert len(coverage_uploads) >= 1
        name = coverage_uploads[0]["with"]["name"]
        assert (
            "python-version" in name or "matrix" in name
        ), "Coverage artifact name should include python version for matrix distinction"
