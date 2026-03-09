"""README badge presence tests.

Covers: TS-009
"""

from __future__ import annotations


class TestReadmeBadges:
    """TS-009: Repository displays CI status and Codecov badges in README."""

    def test_ci_status_badge_present(self, readme_content: str) -> None:
        assert "actions/workflows/ci.yml" in readme_content, (
            "README must contain a GitHub Actions CI status badge"
        )

    def test_codecov_badge_present(self, readme_content: str) -> None:
        assert "[![codecov]" in readme_content, (
            "README must contain a Codecov coverage badge"
        )

    def test_badges_are_markdown_images(self, readme_content: str) -> None:
        assert "![" in readme_content, "Badges must use markdown image syntax"
