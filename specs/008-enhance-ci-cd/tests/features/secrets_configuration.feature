# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-004
Feature: Simplify CI/CD Secrets Configuration
  As a maintainer, I want CI/CD to require only API keys as secrets so that
  setting up the pipeline requires minimal configuration beyond adding
  credentials.

  @TS-017 @FR-009 @SC-004 @P1 @acceptance
  Scenario: CI completes with only API key secrets configured
    Given a user has only added required API key secrets
    When CI runs
    Then all stages complete without errors related to missing configuration

  @TS-018 @FR-009 @SC-007 @P1 @acceptance
  Scenario: Clear error message for missing secret
    Given a required secret is not configured
    When CI runs
    Then a clear error message indicates which secret is missing

  @TS-019 @FR-009 @SC-007 @P1 @acceptance
  Scenario: Helpful instructions when no secrets configured
    Given no secrets are configured
    When the workflow starts
    Then it fails with helpful instructions for required GitHub secrets

  @TS-020 @FR-009 @P1 @contract
  Scenario: Workflows contain no hardcoded configuration values
    Given all CI workflow files in ".github/workflows/"
    When scanned for hardcoded secrets or configuration values
    Then only secret references via "${{ secrets.* }}" are found
    And no other configuration values are hardcoded

  @TS-021 @FR-009 @P1 @validation
  Scenario: Only one secret is required for full pipeline
    Given the CI workflow configuration
    When all secret references are enumerated
    Then exactly one secret is required: "TESTPYPI_API_TOKEN"
