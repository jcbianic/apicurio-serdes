"""Shared BDD step definitions for deserializer feature files.

Background steps and fixtures used across avro_deserialization.feature,
wire_format.feature, schema_caching.feature, and from_dict_hook.feature.
"""

from __future__ import annotations

from typing import Any

import respx
from pytest_bdd import given, parsers

from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.serialization import MessageField, SerializationContext
from tests.conftest import (
    REGISTRY_URL,
    GROUP_ID,
    USER_EVENT_SCHEMA_JSON,
    VALID_USER_EVENT,
    _id_schema_route,
    _schema_route,
    make_confluent_bytes,
)

# Feature file base path (relative to this file)
FEATURE_DIR = "../../specs/002-avro-deserializer/tests/features"

# Deserializer-specific IDs (note: reversed from serializer defaults)
DESER_CONTENT_ID = 42
DESER_GLOBAL_ID = 7

SCHEMA_B_JSON: dict[str, Any] = {
    "type": "record",
    "name": "SchemaB",
    "namespace": "com.example",
    "fields": [
        {"name": "id", "type": "string"},
    ],
}


# ── Shared Background step definitions ──


@given(
    parsers.cfparse(
        'a configured ApicurioRegistryClient pointing at a registry that holds'
        ' a known Avro schema with contentId {content_id:d} for artifact "{artifact_id}"'
    ),
    target_fixture="registry_client",
)
def given_client_with_content_id(
    mock_registry: respx.MockRouter, content_id: int, artifact_id: str
) -> ApicurioRegistryClient:
    _id_schema_route(mock_registry, "contentId", content_id)
    # Also set up artifact route for round-trip tests (serializer needs it)
    _schema_route(
        mock_registry, artifact_id, global_id=DESER_GLOBAL_ID, content_id=content_id
    )
    return ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)


@given(
    parsers.cfparse(
        'a SerializationContext for topic "{topic}" and field {field}'
    ),
    target_fixture="ctx",
)
def given_ctx(topic: str, field: str) -> SerializationContext:
    return SerializationContext(topic=topic, field=MessageField[field])


@given(
    "valid Confluent-framed Avro bytes produced for that schema",
    target_fixture="valid_bytes",
)
def given_valid_confluent_bytes() -> bytes:
    return make_confluent_bytes(DESER_CONTENT_ID, VALID_USER_EVENT)
