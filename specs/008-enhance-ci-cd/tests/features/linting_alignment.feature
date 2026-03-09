# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-001
Feature: Align Linting Between Pre-Commit and CI
  As a developer, I want pre-commit hooks to use the same linting rules as the
  CI pipeline so that I catch linting errors locally before pushing and never
  see CI failures due to linting issues.

  @TS-001 @FR-001 @SC-001 @P1 @acceptance
  Scenario: Pre-commit catches ruff violations locally
    Given a developer has committed code with ruff violations
    When they run "pre-commit run --all-files"
    Then ruff violations are caught locally before any push

  @TS-002 @FR-001 @FR-003 @SC-001 @P1 @acceptance
  Scenario: CI linting passes when local pre-commit passes
    Given code passes local pre-commit checks
    When CI runs linting checks
    Then CI linting always passes

  @TS-003 @FR-002 @FR-003 @SC-001 @P1 @contract
  Scenario: Pre-commit and CI enforce identical ruff rules and versions
    Given ".pre-commit-config.yaml" and CI linting configuration exist
    When compared
    Then they enforce identical ruff rules and versions

  @TS-004 @FR-002 @P1 @validation
  Scenario: Pre-commit ruff version is pinned to match lock file
    Given ".pre-commit-config.yaml" specifies a ruff-pre-commit revision
    When the revision is compared to the ruff version in "uv.lock"
    Then the versions match exactly

  @TS-005 @FR-001 @P1 @validation
  Scenario: Ruff rules are sourced from pyproject.toml without duplication
    Given ".pre-commit-config.yaml" defines ruff hooks
    When the hook configuration is inspected
    Then no ruff rule overrides are present in the hook arguments
    And ruff reads rules from "pyproject.toml" automatically
