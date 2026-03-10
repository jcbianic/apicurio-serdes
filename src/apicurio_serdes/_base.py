"""Shared base for sync and async Apicurio Registry clients."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx

from apicurio_serdes._errors import (
    RegistryConnectionError,
    SchemaNotFoundError,
)


@dataclass(frozen=True)
class CachedSchema:
    """Internal value object holding a resolved schema and registry metadata.

    Attributes:
        schema: Parsed Avro schema (Python dict, fastavro-ready).
        global_id: Apicurio globalId from X-Registry-GlobalId header.
        content_id: Apicurio contentId from X-Registry-ContentId header.
    """

    schema: dict[str, Any]
    global_id: int
    content_id: int


class _RegistryClientBase:
    """Shared logic for sync and async Apicurio Registry clients.

    Subclasses must set ``_http_client`` and ``_lock`` in their
    ``__init__`` after calling ``super().__init__()``.
    """

    def __init__(self, url: str, group_id: str) -> None:
        if not url:
            raise ValueError("url must not be empty")
        if not group_id:
            raise ValueError("group_id must not be empty")
        self.url = url
        self.group_id = group_id
        self._schema_cache: dict[tuple[str, str], CachedSchema] = {}
        self._id_cache: dict[tuple[str, int], dict[str, Any]] = {}
        self._closed = False

    def _check_closed(self) -> None:
        if self._closed:
            raise RuntimeError("client is closed")

    def _schema_endpoint(self, artifact_id: str) -> str:
        return (
            f"/groups/{self.group_id}"
            f"/artifacts/{artifact_id}"
            "/versions/latest/content"
        )

    @staticmethod
    def _id_endpoint(id_type: str, id_value: int) -> str:
        return f"/ids/{id_type}s/{id_value}"

    def _process_schema_response(
        self, response: httpx.Response, artifact_id: str
    ) -> CachedSchema:
        """Parse an HTTP response from an artifact content endpoint.

        Raises:
            SchemaNotFoundError: On HTTP 404.
            RegistryConnectionError: On other HTTP errors.
            ValueError: If globalId/contentId exceed signed 64-bit range.
        """
        if response.status_code == 404:
            raise SchemaNotFoundError(self.group_id, artifact_id)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RegistryConnectionError(self.url, exc) from exc

        schema = json.loads(response.text)
        global_id = int(response.headers["X-Registry-GlobalId"])
        content_id = int(response.headers["X-Registry-ContentId"])

        int64_min, int64_max = -(2**63), 2**63 - 1
        if not (int64_min <= global_id <= int64_max):
            raise ValueError(f"globalId {global_id} is outside signed 64-bit range")
        if not (int64_min <= content_id <= int64_max):
            raise ValueError(
                f"contentId {content_id} is outside signed 64-bit range"
            )

        return CachedSchema(
            schema=schema,
            global_id=global_id,
            content_id=content_id,
        )

    def _process_id_response(
        self, response: httpx.Response, id_type: str, id_value: int
    ) -> dict[str, Any]:
        """Parse an HTTP response from an ID-based schema endpoint.

        Raises:
            SchemaNotFoundError: On HTTP 404.
            RegistryConnectionError: On other HTTP errors.
        """
        if response.status_code == 404:
            raise SchemaNotFoundError.from_id(id_type, id_value)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RegistryConnectionError(self.url, exc) from exc

        return json.loads(response.content)
