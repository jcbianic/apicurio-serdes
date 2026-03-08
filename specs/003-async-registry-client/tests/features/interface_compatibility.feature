# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-003
Feature: Async client mirrors the sync client interface
  As a Python developer migrating from the sync client to the async variant,
  I want the async client to accept the same constructor parameters and expose
  the same method names as the sync client, so that switching requires only
  adding await and changing the class name.

  @TS-021 @FR-001 @FR-007 @SC-004 @P2 @contract
  Scenario: AsyncApicurioRegistryClient accepts the same constructor parameters as the sync client
    Given the sync client is constructed with AsyncApicurioRegistryClient(url="http://registry:8080/apis/registry/v3", group_id="my-group")
    When AsyncApicurioRegistryClient is constructed with the same url and group_id
    Then the async client is initialised successfully with those parameters

  @TS-022 @FR-002 @SC-004 @P2 @contract
  Scenario: get_schema is the method name on the async client
    Given an AsyncApicurioRegistryClient instance
    When the developer calls await client.get_schema(artifact_id) instead of client.get_schema(artifact_id)
    Then the async client responds with the same CachedSchema return type as the sync client

  @TS-023 @FR-005 @FR-006 @SC-004 @P2 @contract
  Scenario Outline: Async client raises the same error types as the sync client
    Given a configured AsyncApicurioRegistryClient
    When a <condition> occurs during get_schema
    Then a <error_type> is raised with the same attributes as the sync client equivalent

    Examples:
      | condition                  | error_type              |
      | registry returns HTTP 404  | SchemaNotFoundError     |
      | registry is unreachable    | RegistryConnectionError |

  @TS-024 @FR-011 @P1 @contract
  Scenario: AsyncApicurioRegistryClient is importable from the top-level package
    When the developer runs: from apicurio_serdes import AsyncApicurioRegistryClient
    Then the import succeeds without error
    And AsyncApicurioRegistryClient is the same class as apicurio_serdes._async_client.AsyncApicurioRegistryClient
