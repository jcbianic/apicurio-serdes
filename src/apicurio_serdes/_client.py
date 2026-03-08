"""Apicurio Registry v3 HTTP client with schema caching."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from typing import Any

import httpx

from apicurio_serdes._errors import (
    RegistryConnectionError,
    SchemaNotFoundError,
)


@dataclass
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


class ApicurioRegistryClient:
    """HTTP client for the Apicurio Registry v3 native API.

    Handles schema retrieval by group_id / artifact_id with
    built-in caching. Thread-safe for read operations.

    Args:
        url: Base URL of the Apicurio Registry v3 API.
             Example: "http://registry:8080/apis/registry/v3"
        group_id: Schema group identifier. Applied to every
                  schema lookup made by this client instance.

    Raises:
        ValueError: If url or group_id is empty.
    """

    def __init__(self, url: str, group_id: str) -> None:
        if not url:
            raise ValueError("url must not be empty")
        if not group_id:
            raise ValueError("group_id must not be empty")
        self.url = url
        self.group_id = group_id
        self._http_client = httpx.Client(base_url=url)
        self._schema_cache: dict[tuple[str, str], CachedSchema] = {}
        self._id_cache: dict[tuple[str, int], dict[str, Any]] = {}
        self._lock = threading.RLock()

    def get_schema(self, artifact_id: str) -> CachedSchema:
        """Retrieve an Avro schema by artifact ID.

        Returns a cached result on subsequent calls for the same
        artifact_id (FR-006).

        Args:
            artifact_id: The artifact identifier within the configured group.

        Returns:
            CachedSchema with parsed schema and content_id.

        Raises:
            SchemaNotFoundError: If the artifact does not exist (HTTP 404).
            RegistryConnectionError: If the registry is unreachable.
        """
        cache_key = (self.group_id, artifact_id)
        if cache_key in self._schema_cache:
            return self._schema_cache[cache_key]

        with self._lock:
            # Double-check after acquiring the lock (NFR-001)
            if cache_key in self._schema_cache:
                return self._schema_cache[cache_key]

            endpoint = (
                f"/groups/{self.group_id}"
                f"/artifacts/{artifact_id}"
                "/versions/latest/content"
            )
            try:
                response = self._http_client.get(endpoint)
            except httpx.ConnectError as exc:
                raise RegistryConnectionError(self.url, exc) from exc

            if response.status_code == 404:
                raise SchemaNotFoundError(self.group_id, artifact_id)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise RegistryConnectionError(self.url, exc) from exc

            schema = json.loads(response.text)
            global_id = int(response.headers["X-Registry-GlobalId"])
            content_id = int(response.headers["X-Registry-ContentId"])

            cached = CachedSchema(
                schema=schema,
                global_id=global_id,
                content_id=content_id,
            )
            self._schema_cache[cache_key] = cached
            return cached

    def get_schema_by_global_id(self, global_id: int) -> dict[str, Any]:
        """Retrieve an Avro schema by its globalId.

        Returns a cached result on subsequent calls for the same
        globalId (FR-007).

        Args:
            global_id: The globalId from the wire format header.

        Returns:
            Parsed Avro schema as a Python dict.

        Raises:
            SchemaNotFoundError: If no schema exists for this globalId (FR-010).
            RegistryConnectionError: If the registry is unreachable (FR-012).
        """
        return self._get_schema_by_id("globalId", global_id)

    def get_schema_by_content_id(self, content_id: int) -> dict[str, Any]:
        """Retrieve an Avro schema by its contentId.

        Returns a cached result on subsequent calls for the same
        contentId (FR-007).

        Args:
            content_id: The contentId from the wire format header.

        Returns:
            Parsed Avro schema as a Python dict.

        Raises:
            SchemaNotFoundError: If no schema exists for this contentId (FR-010).
            RegistryConnectionError: If the registry is unreachable (FR-012).
        """
        return self._get_schema_by_id("contentId", content_id)

    def _get_schema_by_id(self, id_type: str, id_value: int) -> dict[str, Any]:
        """Shared implementation for ID-based schema lookups (D12)."""
        cache_key = (id_type, id_value)
        if cache_key in self._id_cache:
            return self._id_cache[cache_key]

        with self._lock:
            if cache_key in self._id_cache:
                return self._id_cache[cache_key]

            endpoint = f"/ids/{id_type}s/{id_value}"
            try:
                response = self._http_client.get(endpoint)
            except httpx.ConnectError as exc:
                raise RegistryConnectionError(self.url, exc) from exc

            if response.status_code == 404:
                raise SchemaNotFoundError.from_id(id_type, id_value)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise RegistryConnectionError(self.url, exc) from exc

            schema: dict[str, Any] = json.loads(response.content)
            self._id_cache[cache_key] = schema
            return schema
