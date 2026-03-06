"""Shared test fixtures for apicurio-serdes tests."""

from __future__ import annotations

import json
from typing import Any

import pytest
import respx
from httpx import Response

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


@pytest.fixture()
def mock_registry() -> respx.MockRouter:
    """Provide a started respx mock router for the registry."""
    with respx.mock(assert_all_called=False) as router:
        yield router
