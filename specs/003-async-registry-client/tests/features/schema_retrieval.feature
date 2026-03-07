# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-001
Feature: Async schema retrieval from Apicurio Registry
  As a Python developer building an asyncio-based Kafka producer or consumer,
  I want an async registry client that retrieves Avro schemas without blocking
  the event loop, so that I can integrate schema-validated serialization into
  my async application without thread-pool workarounds.

  Background:
    Given a configured AsyncApicurioRegistryClient pointing at a stubbed registry

  @TS-001 @FR-001 @FR-002 @SC-001 @P1 @acceptance
  Scenario: Successful async schema retrieval returns CachedSchema
    Given the registry holds a known Avro schema for artifact "UserEvent" with global_id 42 and content_id 7
    When await client.get_schema("UserEvent") is called
    Then the returned CachedSchema contains the parsed Avro schema dict
    And the CachedSchema global_id is 42
    And the CachedSchema content_id is 7

  @TS-002 @FR-005 @P1 @acceptance
  Scenario: Artifact not found raises SchemaNotFoundError
    Given the registry returns HTTP 404 for artifact "NonExistentArtifact"
    When await client.get_schema("NonExistentArtifact") is called
    Then a SchemaNotFoundError is raised
    And the error identifies artifact "NonExistentArtifact" and the configured group_id

  @TS-003 @FR-006 @P1 @acceptance
  Scenario: Registry unreachable raises RegistryConnectionError
    Given the registry is unreachable due to a network error
    When await client.get_schema("UserEvent") is called
    Then a RegistryConnectionError is raised
    And the error wraps the underlying network exception
    And the error includes the registry base URL

  @TS-004 @FR-007 @P1 @contract
  Scenario: group_id is applied to every schema lookup
    Given the client is configured with group_id "my-group"
    And the registry holds a schema for artifact "OrderCreated" in group "my-group"
    When await client.get_schema("OrderCreated") is called
    Then the HTTP request targets the endpoint for group "my-group" and artifact "OrderCreated"

  @TS-005 @FR-003 @SC-002 @P1 @contract
  Scenario: get_schema returns the shared CachedSchema type
    Given the registry holds a known Avro schema for artifact "UserEvent" with global_id 1 and content_id 1
    When await client.get_schema("UserEvent") is called
    Then the returned object is an instance of CachedSchema from apicurio_serdes._client
