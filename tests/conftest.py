"""Shared test fixtures for apicurio-serdes tests."""

from __future__ import annotations

import io
import json
import struct
from collections.abc import Generator
from typing import Any

import fastavro
import pytest
import respx
from httpx import Response
from pytest_bdd import given, parsers

from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroSerializer

REGISTRY_URL = "http://registry:8080/apis/registry/v3"
GROUP_ID = "test-group"

USER_EVENT_SCHEMA_JSON: dict[str, Any] = {
    "type": "record",
    "name": "UserEvent",
    "namespace": "com.example",
    "fields": [
        {"name": "userId", "type": "string"},
        {"name": "country", "type": "string"},
    ],
}

VALID_USER_EVENT: dict[str, Any] = {"userId": "abc-123", "country": "FR"}

VALID_USER_EVENT_ALT: dict[str, Any] = {"userId": "def-456", "country": "DE"}

INVALID_USER_EVENT_MISSING_FIELD: dict[str, Any] = {"userId": "abc-123"}

VALID_USER_EVENT_EXTRA_FIELDS: dict[str, Any] = {
    "userId": "abc-123",
    "country": "FR",
    "extra_field": "should_be_dropped",
}

GLOBAL_ID = 42
CONTENT_ID = 7


def _schema_route(
    router: respx.MockRouter,
    artifact_id: str,
    *,
    schema: dict[str, Any] = USER_EVENT_SCHEMA_JSON,
    global_id: int = GLOBAL_ID,
    content_id: int = CONTENT_ID,
) -> respx.Route:
    """Register a mock route that returns a schema for a given artifact."""
    url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/{artifact_id}/versions/latest/content"
    return router.get(url).mock(
        return_value=Response(
            200,
            content=json.dumps(schema),
            headers={
                "X-Registry-GlobalId": str(global_id),
                "X-Registry-ContentId": str(content_id),
            },
        )
    )


def _not_found_route(
    router: respx.MockRouter,
    artifact_id: str,
) -> respx.Route:
    """Register a mock route that returns 404 for a given artifact."""
    url = f"{REGISTRY_URL}/groups/{GROUP_ID}/artifacts/{artifact_id}/versions/latest/content"
    return router.get(url).mock(
        return_value=Response(
            404,
            json={
                "error_code": 404,
                "message": f"No artifact with ID '{artifact_id}' in group '{GROUP_ID}' was found.",
            },
        )
    )


def _id_schema_route(
    router: respx.MockRouter,
    id_type: str,
    id_value: int,
    *,
    schema: dict[str, Any] = USER_EVENT_SCHEMA_JSON,
) -> respx.Route:
    """Register a mock route for an ID-based schema lookup (globalId/contentId)."""
    url = f"{REGISTRY_URL}/ids/{id_type}s/{id_value}"
    return router.get(url).mock(
        return_value=Response(200, content=json.dumps(schema).encode())
    )


def _id_not_found_route(
    router: respx.MockRouter,
    id_type: str,
    id_value: int,
) -> respx.Route:
    """Register a mock 404 route for an ID-based schema lookup."""
    url = f"{REGISTRY_URL}/ids/{id_type}s/{id_value}"
    return router.get(url).mock(
        return_value=Response(
            404,
            json={
                "error_code": 404,
                "message": f"No schema with {id_type} '{id_value}' found.",
            },
        )
    )


def make_confluent_bytes(
    schema_id: int,
    data: dict[str, Any],
    schema: dict[str, Any] | None = None,
) -> bytes:
    """Build Confluent wire format bytes: 0x00 + 4-byte ID + Avro payload."""
    if schema is None:
        schema = USER_EVENT_SCHEMA_JSON
    parsed = fastavro.parse_schema(json.loads(json.dumps(schema)))
    buf = io.BytesIO()
    fastavro.schemaless_writer(buf, parsed, data)
    return b"\x00" + struct.pack(">I", schema_id) + buf.getvalue()


@pytest.fixture()
def mock_registry() -> Generator[respx.MockRouter, None, None]:
    """Provide a started respx mock router for the registry."""
    with respx.mock(assert_all_called=False) as router:
        yield router


# ── Shared Background step (wire_format.feature — serializer + deserializer) ──


@given(
    parsers.cfparse(
        "a configured ApicurioRegistryClient pointing at a registry that returns"
        ' globalId {global_id:d} and contentId {content_id:d} for artifact "{artifact_id}"'
    ),
    target_fixture="registry_client",
)
def given_client_with_global_and_content_ids(
    mock_registry: respx.MockRouter, global_id: int, content_id: int, artifact_id: str
) -> ApicurioRegistryClient:
    _schema_route(
        mock_registry, artifact_id, global_id=global_id, content_id=content_id
    )
    _id_schema_route(mock_registry, "globalId", global_id)
    _id_schema_route(mock_registry, "contentId", content_id)
    return ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)


# ── Background step definitions (avro_serialization.feature) ──


@given(
    parsers.cfparse(
        'a configured ApicurioRegistryClient pointing at a registry that holds a known Avro schema for artifact "{artifact_id}"'
    ),
    target_fixture="registry_client",
)
def given_configured_client(
    mock_registry: respx.MockRouter, artifact_id: str
) -> ApicurioRegistryClient:
    _schema_route(mock_registry, artifact_id)
    return ApicurioRegistryClient(url=REGISTRY_URL, group_id=GROUP_ID)


@given(
    parsers.cfparse(
        'an AvroSerializer created with that client and artifact_id "{artifact_id}"'
    ),
    target_fixture="serializer",
)
def given_serializer(
    registry_client: ApicurioRegistryClient, artifact_id: str
) -> AvroSerializer:
    return AvroSerializer(registry_client=registry_client, artifact_id=artifact_id)
