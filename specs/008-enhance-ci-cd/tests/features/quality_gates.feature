# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-005
Feature: Implement Quality Gates as Required Status Checks
  As a repository owner, I want quality gates (tests, coverage, linting, type
  checking) to be enforced as required status checks so that no PR can merge
  without meeting quality standards.

  @TS-022 @FR-010 @FR-014 @SC-005 @P2 @acceptance
  Scenario: Merge blocked when coverage fails
    Given a PR fails test coverage requirements
    When review is complete
    Then the merge button remains disabled until coverage passes

  @TS-023 @FR-010 @FR-014 @SC-005 @P2 @acceptance
  Scenario: Merge enabled when all quality gates pass
    Given all quality gates pass
    When the PR is approved
    Then the merge button is enabled

  @TS-024 @FR-010 @SC-005 @P2 @acceptance
  Scenario: Failing check is clearly visible with error details
    Given a quality gate fails
    When a maintainer reviews the PR
    Then the failing check is clearly visible with error details

  @TS-025 @FR-010 @P2 @contract
  Scenario: CI defines required quality gate status checks
    Given the CI workflow configuration
    When the job names are inspected
    Then the following status checks are defined: "lint", "typecheck", "test", "docs-build"

  @TS-026 @FR-014 @SC-005 @P2 @contract
  Scenario: Branch protection requires all status checks
    Given branch protection rules are configured for "main"
    When the required status checks are inspected
    Then all CI quality gate checks are required to pass before merge
