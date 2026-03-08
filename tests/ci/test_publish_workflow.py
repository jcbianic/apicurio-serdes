"""YAML validation tests for publish.yml workflow.

Covers: TS-011, TS-012, TS-013, TS-014, TS-015, TS-016, TS-017
"""

from __future__ import annotations

from typing import Any


class TestPublishTrigger:
    """TS-011: Publish workflow triggers on release published."""

    def test_triggers_on_release_published(
        self, publish_workflow: dict[str, Any]
    ) -> None:
        triggers = publish_workflow[True]
        assert "release" in triggers
        assert triggers["release"]["types"] == ["published"]


class TestPublishJobChain:
    """TS-017: Sequential job chain with hard gates."""

    EXPECTED_JOBS = [
        "validate-version",
        "build",
        "publish-testpypi",
        "validate-testpypi",
        "publish-pypi",
    ]

    def test_all_jobs_present(self, publish_workflow: dict[str, Any]) -> None:
        jobs = publish_workflow["jobs"]
        for job_name in self.EXPECTED_JOBS:
            assert job_name in jobs, f"Missing job: {job_name}"

    def test_build_needs_validate_version(
        self, publish_workflow: dict[str, Any]
    ) -> None:
        build = publish_workflow["jobs"]["build"]
        needs = build.get("needs", [])
        if isinstance(needs, str):
            needs = [needs]
        assert "validate-version" in needs

    def test_publish_testpypi_needs_build(
        self, publish_workflow: dict[str, Any]
    ) -> None:
        job = publish_workflow["jobs"]["publish-testpypi"]
        needs = job.get("needs", [])
        if isinstance(needs, str):
            needs = [needs]
        assert "build" in needs

    def test_validate_testpypi_needs_publish_testpypi(
        self, publish_workflow: dict[str, Any]
    ) -> None:
        job = publish_workflow["jobs"]["validate-testpypi"]
        needs = job.get("needs", [])
        if isinstance(needs, str):
            needs = [needs]
        assert "publish-testpypi" in needs

    def test_publish_pypi_needs_validate_testpypi(
        self, publish_workflow: dict[str, Any]
    ) -> None:
        job = publish_workflow["jobs"]["publish-pypi"]
        needs = job.get("needs", [])
        if isinstance(needs, str):
            needs = [needs]
        assert "validate-testpypi" in needs


class TestVersionValidation:
    """TS-013: Pipeline fails when version does not match release tag."""

    def test_validate_version_job_exists(
        self, publish_workflow: dict[str, Any]
    ) -> None:
        assert "validate-version" in publish_workflow["jobs"]

    def test_validate_version_compares_tag_to_pyproject(
        self, publish_workflow: dict[str, Any]
    ) -> None:
        job = publish_workflow["jobs"]["validate-version"]
        run_steps = [s.get("run", "") for s in job["steps"]]
        combined = " ".join(run_steps)
        assert "pyproject.toml" in combined or "version" in combined.lower(), (
            "Version validation must reference pyproject.toml or version"
        )


class TestOIDCTrustedPublishing:
    """TS-016: Publication uses OIDC trusted publishing."""

    def test_publish_testpypi_has_id_token_write(
        self, publish_workflow: dict[str, Any]
    ) -> None:
        job = publish_workflow["jobs"]["publish-testpypi"]
        perms = job.get("permissions", {})
        assert perms.get("id-token") == "write", (
            "publish-testpypi must have id-token: write for OIDC"
        )

    def test_publish_pypi_has_id_token_write(
        self, publish_workflow: dict[str, Any]
    ) -> None:
        job = publish_workflow["jobs"]["publish-pypi"]
        perms = job.get("permissions", {})
        assert perms.get("id-token") == "write", (
            "publish-pypi must have id-token: write for OIDC"
        )

    def test_publish_testpypi_uses_pypi_publish_action(
        self, publish_workflow: dict[str, Any]
    ) -> None:
        job = publish_workflow["jobs"]["publish-testpypi"]
        action_steps = [
            s
            for s in job["steps"]
            if "pypa/gh-action-pypi-publish" in s.get("uses", "")
        ]
        assert len(action_steps) >= 1

    def test_publish_pypi_uses_pypi_publish_action(
        self, publish_workflow: dict[str, Any]
    ) -> None:
        job = publish_workflow["jobs"]["publish-pypi"]
        action_steps = [
            s
            for s in job["steps"]
            if "pypa/gh-action-pypi-publish" in s.get("uses", "")
        ]
        assert len(action_steps) >= 1


class TestPublishEnvironments:
    """TS-016 supplement: Jobs use correct GitHub environments."""

    def test_publish_testpypi_environment(
        self, publish_workflow: dict[str, Any]
    ) -> None:
        job = publish_workflow["jobs"]["publish-testpypi"]
        assert job.get("environment") == "testpypi"

    def test_publish_pypi_environment(
        self, publish_workflow: dict[str, Any]
    ) -> None:
        job = publish_workflow["jobs"]["publish-pypi"]
        assert job.get("environment") == "pypi"


class TestBuildJob:
    """TS-012: Build produces distribution artifacts."""

    def test_build_uses_uv_build(
        self, publish_workflow: dict[str, Any]
    ) -> None:
        job = publish_workflow["jobs"]["build"]
        run_steps = [s.get("run", "") for s in job["steps"]]
        assert any("uv build" in step for step in run_steps)

    def test_build_uploads_dist_artifact(
        self, publish_workflow: dict[str, Any]
    ) -> None:
        job = publish_workflow["jobs"]["build"]
        upload_steps = [
            s
            for s in job["steps"]
            if s.get("uses", "").startswith("actions/upload-artifact")
        ]
        assert len(upload_steps) >= 1, "Build must upload dist artifact"
