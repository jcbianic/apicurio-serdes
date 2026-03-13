"""Apicurio Registry v3 HTTP client with schema caching."""

from __future__ import annotations

import threading
from typing import Any

import httpx

from apicurio_serdes._base import CachedSchema, _RegistryClientBase
from apicurio_serdes._errors import RegistryConnectionError

# Re-export so ``from apicurio_serdes._client import CachedSchema`` keeps working.
__all__ = ["ApicurioRegistryClient", "CachedSchema"]


class ApicurioRegistryClient(_RegistryClientBase):
    """HTTP client for the Apicurio Registry v3 native API.

    Handles schema retrieval by group_id / artifact_id with
    built-in caching. Thread-safe for read operations.

    Args:
        url: Base URL of the Apicurio Registry v3 API.
             Example: ``"http://registry:8080/apis/registry/v3"``.
        group_id: Schema group identifier. Applied to every
                  schema lookup made by this client instance.
        auth: Optional httpx authentication handler. Pass a
              :class:`~apicurio_serdes.BearerAuth` or
              :class:`~apicurio_serdes.KeycloakAuth` instance for
              authenticated registries. Defaults to ``None`` (no auth).

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

    def __init__(
        self, url: str, group_id: str, auth: httpx.Auth | None = None
    ) -> None:
        super().__init__(url, group_id)
        self._http_client = httpx.Client(base_url=url, auth=auth)
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
            RuntimeError: If the client has been closed.
        """
        self._check_closed()
        cache_key = (self.group_id, artifact_id)
        if cache_key in self._schema_cache:
            return self._schema_cache[cache_key]

        with self._lock:
            # Double-check after acquiring the lock (NFR-001)
            if cache_key in self._schema_cache:
                return self._schema_cache[cache_key]

            try:
                response = self._http_client.get(self._schema_endpoint(artifact_id))
            except httpx.TransportError as exc:
                raise RegistryConnectionError(self.url, exc) from exc

            cached = self._process_schema_response(response, artifact_id)
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
            RuntimeError: If the client has been closed.
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
            RuntimeError: If the client has been closed.
        """
        return self._get_schema_by_id("contentId", content_id)

    def _get_schema_by_id(self, id_type: str, id_value: int) -> dict[str, Any]:
        """Shared implementation for ID-based schema lookups (D12)."""
        self._check_closed()
        cache_key = (id_type, id_value)
        if cache_key in self._id_cache:
            return self._id_cache[cache_key]

        with self._lock:
            if cache_key in self._id_cache:
                return self._id_cache[cache_key]

            try:
                response = self._http_client.get(self._id_endpoint(id_type, id_value))
            except httpx.TransportError as exc:
                raise RegistryConnectionError(self.url, exc) from exc

            schema = self._process_id_response(response, id_type, id_value)
            self._id_cache[cache_key] = schema
            return schema

    def close(self) -> None:
        """Close the underlying HTTP connection pool.

        Call this when the client is no longer needed and you are not
        using it as a context manager. Safe to call multiple times.
        """
        self._closed = True
        self._http_client.close()

    def __enter__(self) -> ApicurioRegistryClient:
        """Enter the context manager. Returns self."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit the context manager. Calls close()."""
        self.close()
