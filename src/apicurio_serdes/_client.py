"""Apicurio Registry v3 HTTP client with schema caching."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from typing import Any

import httpx

from apicurio_serdes._errors import RegistryConnectionError, SchemaNotFoundError


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
             Example: ``"http://registry:8080/apis/registry/v3"``.
        group_id: Schema group identifier. Applied to every
                  schema lookup made by this client instance.

    Raises:
        ValueError: If *url* or *group_id* is empty.

    Example:
        ```python
        from apicurio_serdes import ApicurioRegistryClient

        client = ApicurioRegistryClient(
            url="http://localhost:8080/apis/registry/v3",
            group_id="com.example.schemas",
        )
        schema = client.get_schema("UserEvent")
        ```
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
            response.raise_for_status()

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
