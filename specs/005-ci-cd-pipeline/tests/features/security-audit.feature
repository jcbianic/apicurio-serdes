# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-004
Feature: Automated Security Audit
  As a maintainer, I want automated security scanning on every change and on a
  recurring schedule so that known vulnerabilities in dependencies and in the
  codebase are detected early and do not reach production.

  @TS-018 @FR-013 @SC-005 @P2 @acceptance
  Scenario: Dependency vulnerabilities are reported when a pull request changes dependencies
    Given a pull request introduces or updates a dependency
    When the security audit runs
    Then it reports any known vulnerabilities in the dependency tree

  @TS-019 @FR-014 @SC-005 @P2 @acceptance
  Scenario: Scheduled audit creates an alert when vulnerabilities are found in existing dependencies
    Given the security audit runs on a scheduled basis
    When vulnerabilities are found in existing dependencies
    Then a notification or issue is created to alert maintainers

  @TS-020 @FR-015 @P2 @acceptance
  Scenario: Static security analysis reports findings with severity and location
    Given the codebase contains a static analysis security finding
    When the security audit runs
    Then it reports the finding with severity and location

  @TS-021 @FR-013 @FR-014 @SC-005 @P2 @contract
  Scenario: Security workflow executes on pull requests targeting main
    Given the security workflow is configured
    When a pull request targets the main branch
    Then the dependency-audit and codeql jobs execute

  @TS-022 @FR-014 @SC-005 @P2 @contract
  Scenario: Security workflow executes on weekly schedule against the default branch
    Given the security workflow is configured with a weekly schedule
    When the scheduled trigger fires on Monday at 06:00 UTC
    Then the dependency-audit and codeql jobs execute against the default branch
