# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

Feature: AsyncApicurioRegistryClient input validation
  The async client validates constructor parameters at construction time
  to surface misconfiguration errors immediately rather than at first use.

  @TS-041 @FR-008 @P2 @validation
  Scenario Outline: Empty constructor parameters raise ValueError
    When AsyncApicurioRegistryClient is constructed with url="<url>" and group_id="<group_id>"
    Then a ValueError is raised with message "<message>"

    Examples:
      | url                                      | group_id  | message                  |
      |                                          | my-group  | url must not be empty    |
      | http://registry:8080/apis/registry/v3   |           | group_id must not be empty |
