"""YAML validation tests for ci.yml Codecov integration.

Covers: TS-007, TS-008, TS-010
"""

from __future__ import annotations

from typing import Any


class TestCodecovUpload:
    """TS-007, TS-008: Coverage results uploaded to Codecov."""

    def test_test_job_has_codecov_action_step(
        self, ci_workflow: dict[str, Any]
    ) -> None:
        test_job = ci_workflow["jobs"]["test"]
        codecov_steps = [
            s
            for s in test_job["steps"]
            if s.get("uses", "").startswith("codecov/codecov-action")
        ]
        assert len(codecov_steps) >= 1, "Test job must have a codecov-action step"

    def test_codecov_action_is_sha_pinned(self, ci_workflow: dict[str, Any]) -> None:
        test_job = ci_workflow["jobs"]["test"]
        codecov_steps = [
            s
            for s in test_job["steps"]
            if s.get("uses", "").startswith("codecov/codecov-action")
        ]
        uses = codecov_steps[0]["uses"]
        ref = uses.split("@", 1)[1]
        assert len(ref) == 40 and all(c in "0123456789abcdef" for c in ref), (
            f"Codecov action must be pinned to a commit SHA, got: {uses}"
        )

    def test_codecov_uploads_coverage_xml(
        self, ci_workflow: dict[str, Any]
    ) -> None:
        test_job = ci_workflow["jobs"]["test"]
        codecov_steps = [
            s
            for s in test_job["steps"]
            if s.get("uses", "").startswith("codecov/codecov-action")
        ]
        files = codecov_steps[0].get("with", {}).get("files", "")
        assert "coverage.xml" in files


class TestCodecovNonBlocking:
    """TS-010: Coverage service unavailability does not block CI."""

    def test_codecov_fail_ci_if_error_is_false(
        self, ci_workflow: dict[str, Any]
    ) -> None:
        test_job = ci_workflow["jobs"]["test"]
        codecov_steps = [
            s
            for s in test_job["steps"]
            if s.get("uses", "").startswith("codecov/codecov-action")
        ]
        fail_ci = codecov_steps[0].get("with", {}).get("fail_ci_if_error", True)
        assert fail_ci is False, "Codecov must not block CI if upload fails"


class TestUploadArtifactBeforeCodecov:
    """TS-006 supplement: upload-artifact step precedes codecov step."""

    def test_upload_artifact_before_codecov(
        self, ci_workflow: dict[str, Any]
    ) -> None:
        test_job = ci_workflow["jobs"]["test"]
        steps = test_job["steps"]
        upload_idx = next(
            (
                i
                for i, s in enumerate(steps)
                if s.get("uses", "").startswith("actions/upload-artifact")
            ),
            None,
        )
        codecov_idx = next(
            (
                i
                for i, s in enumerate(steps)
                if s.get("uses", "").startswith("codecov/codecov-action")
            ),
            None,
        )
        assert upload_idx is not None, "Must have upload-artifact step"
        assert codecov_idx is not None, "Must have codecov step"
        assert upload_idx < codecov_idx, (
            "upload-artifact must come before codecov-action"
        )
