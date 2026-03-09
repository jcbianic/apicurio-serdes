"""YAML validation tests for dependabot.yml configuration.

Covers: TS-019
"""

from __future__ import annotations

from typing import Any


class TestDependabotConfig:
    """TS-019: Dependabot configuration for pip and github-actions."""

    def test_version_is_2(self, dependabot_config: dict[str, Any]) -> None:
        assert dependabot_config["version"] == 2

    def test_has_pip_ecosystem(self, dependabot_config: dict[str, Any]) -> None:
        ecosystems = [u["package-ecosystem"] for u in dependabot_config["updates"]]
        assert "pip" in ecosystems

    def test_has_github_actions_ecosystem(
        self, dependabot_config: dict[str, Any]
    ) -> None:
        ecosystems = [u["package-ecosystem"] for u in dependabot_config["updates"]]
        assert "github-actions" in ecosystems

    def test_pip_schedule_is_daily(self, dependabot_config: dict[str, Any]) -> None:
        pip_updates = [
            u for u in dependabot_config["updates"] if u["package-ecosystem"] == "pip"
        ]
        assert len(pip_updates) == 1
        assert pip_updates[0]["schedule"]["interval"] == "daily"

    def test_github_actions_schedule_is_weekly(
        self, dependabot_config: dict[str, Any]
    ) -> None:
        ga_updates = [
            u
            for u in dependabot_config["updates"]
            if u["package-ecosystem"] == "github-actions"
        ]
        assert len(ga_updates) == 1
        assert ga_updates[0]["schedule"]["interval"] == "weekly"

    def test_pip_directory_is_root(self, dependabot_config: dict[str, Any]) -> None:
        pip_updates = [
            u for u in dependabot_config["updates"] if u["package-ecosystem"] == "pip"
        ]
        assert pip_updates[0]["directory"] == "/"

    def test_github_actions_directory_is_root(
        self, dependabot_config: dict[str, Any]
    ) -> None:
        ga_updates = [
            u
            for u in dependabot_config["updates"]
            if u["package-ecosystem"] == "github-actions"
        ]
        assert ga_updates[0]["directory"] == "/"
