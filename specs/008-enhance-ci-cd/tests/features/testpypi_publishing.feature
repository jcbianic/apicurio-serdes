# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-002
Feature: Publish Package to TestPyPI on Pull Requests
  As a maintainer, I want every PR to automatically publish a pre-release
  version to TestPyPI so that reviewers and testers can install and validate
  the package before merge.

  @TS-006 @FR-004 @SC-002 @P1 @acceptance
  Scenario: Pre-release package published to TestPyPI on PR
    Given a PR is opened
    When CI completes successfully
    Then a pre-release package is published to TestPyPI

  @TS-007 @FR-004 @SC-002 @P1 @acceptance
  Scenario: TestPyPI package is installable
    Given a TestPyPI package version exists
    When a user runs "pip install --index-url https://test.pypi.org/simple/"
    Then the package installs correctly

  @TS-008 @FR-004 @SC-002 @P1 @acceptance
  Scenario: New pre-release version published on PR update
    Given a PR is updated with new commits
    When CI runs again
    Then a new pre-release version is published

  @TS-009 @FR-004 @P1 @contract
  Scenario: Pre-release version follows PEP 440 rcN format
    Given the base version in "pyproject.toml" is "X.Y.Z"
    And the GitHub Actions run number is "N"
    When the CI publish-testpypi job builds the package
    Then the published version is "X.Y.ZrcN"

  @TS-010 @FR-005 @P1 @contract
  Scenario: TestPyPI publishing uses API token secret
    Given the CI workflow defines a "publish-testpypi" job
    When the job configuration is inspected
    Then it authenticates using the "TESTPYPI_API_TOKEN" GitHub secret

  @TS-011 @FR-004 @P1 @validation
  Scenario: Parallel PRs produce unique version numbers
    Given two PRs are open simultaneously
    When both trigger the publish-testpypi job
    Then each produces a unique version number based on run number
    And no version conflict occurs on TestPyPI
