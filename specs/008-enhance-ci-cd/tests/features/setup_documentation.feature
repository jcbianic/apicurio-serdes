# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-007
Feature: Document API Key Setup Instructions
  As a new maintainer setting up the repository, I want clear instructions for
  configuring GitHub secrets so that I know exactly which API keys to add and
  where to obtain them.

  @TS-033 @FR-015 @SC-004 @P3 @acceptance
  Scenario: Documentation enables successful secret configuration
    Given a user reads the API key setup documentation
    When they follow the steps
    Then they can successfully add all required secrets to GitHub

  @TS-034 @FR-015 @SC-004 @P3 @acceptance
  Scenario: Documentation lists secret names, values, and sources
    Given the documentation is complete
    When a user configures secrets
    Then they know the names, values, and sources for each secret

  @TS-035 @FR-015 @SC-007 @P3 @acceptance
  Scenario: Troubleshooting steps for misconfigured secrets
    Given a secret is misconfigured
    When they reference the documentation
    Then troubleshooting steps help identify and fix the issue

  @TS-036 @FR-015 @P3 @validation
  Scenario: Setup documentation exists at expected path
    Given the repository file structure
    When "docs/setup/ci-cd-secrets.md" is checked
    Then the file exists and contains secret configuration instructions

  @TS-037 @FR-015 @P3 @validation
  Scenario: Documentation covers all required secrets
    Given the setup documentation
    When the listed secrets are compared to CI workflow secret references
    Then every secret used in workflows is documented with name, source, and instructions
