"""Async Apicurio Registry v3 HTTP client with schema caching."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import httpx

from apicurio_serdes._base import CachedSchema, _RegistryClientBase
from apicurio_serdes._errors import RegistryConnectionError

if TYPE_CHECKING:
    from typing import Literal


class AsyncApicurioRegistryClient(_RegistryClientBase):
    """Async HTTP client for the Apicurio Registry v3 native API.

    Non-blocking counterpart to ApicurioRegistryClient. Uses
    httpx.AsyncClient for async I/O. Safe for concurrent use
    from multiple coroutines within the same event loop.

    Args:
        url: Base URL of the Apicurio Registry v3 API.
             Example: "http://registry:8080/apis/registry/v3"
        group_id: Schema group identifier. Applied to every
                  schema lookup made by this client instance.

    Raises:
        ValueError: If url or group_id is empty.
    """

    def __init__(self, url: str, group_id: str) -> None:
        super().__init__(url, group_id)
        self._http_client = httpx.AsyncClient(base_url=url)
        self._lock = asyncio.Lock()

    async def get_schema(self, artifact_id: str) -> CachedSchema:
        """Retrieve an Avro schema by artifact ID (async).

        Returns a cached result on subsequent calls for the same
        artifact_id. Safe for concurrent invocation: concurrent
        first-time fetches for the same artifact_id result in
        exactly one HTTP request (NFR-001).

        Args:
            artifact_id: The artifact identifier within the configured group.

        Returns:
            CachedSchema with parsed schema dict, global_id, and content_id.

        Raises:
            SchemaNotFoundError: If the artifact does not exist (HTTP 404).
            RegistryConnectionError: If the registry is unreachable or returns
                an unexpected HTTP status code.
            RuntimeError: If the client has been closed.
        """
        self._check_closed()
        cache_key = (self.group_id, artifact_id)
        if cache_key in self._schema_cache:
            return self._schema_cache[cache_key]

        async with self._lock:
            if cache_key in self._schema_cache:
                return self._schema_cache[cache_key]

            try:
                response = await self._http_client.get(
                    self._schema_endpoint(artifact_id)
                )
            except httpx.TransportError as exc:
                raise RegistryConnectionError(self.url, exc) from exc

            cached = self._process_schema_response(response, artifact_id)
            self._schema_cache[cache_key] = cached
            return cached

    async def get_schema_by_global_id(self, global_id: int) -> dict[str, Any]:
        """Retrieve an Avro schema by its globalId (async).

        Returns a cached result on subsequent calls for the same globalId.

        Args:
            global_id: The globalId from the wire format header.

        Returns:
            Parsed Avro schema as a Python dict.

        Raises:
            SchemaNotFoundError: If no schema exists for this globalId.
            RegistryConnectionError: If the registry is unreachable.
            RuntimeError: If the client has been closed.
        """
        return await self._get_schema_by_id("globalId", global_id)

    async def get_schema_by_content_id(self, content_id: int) -> dict[str, Any]:
        """Retrieve an Avro schema by its contentId (async).

        Returns a cached result on subsequent calls for the same contentId.

        Args:
            content_id: The contentId from the wire format header.

        Returns:
            Parsed Avro schema as a Python dict.

        Raises:
            SchemaNotFoundError: If no schema exists for this contentId.
            RegistryConnectionError: If the registry is unreachable.
            RuntimeError: If the client has been closed.
        """
        return await self._get_schema_by_id("contentId", content_id)

    async def register_schema(
        self,
        artifact_id: str,
        schema: dict[str, Any],
        if_exists: Literal["FAIL", "RETURN", "RETURN_OR_UPDATE", "UPDATE"] = "RETURN",
    ) -> CachedSchema:
        """Register a schema artifact with the registry (async).

        Posts the schema to the registry under the configured group. On success,
        populates the internal cache so subsequent ``get_schema`` calls are cache
        hits with no additional HTTP request.

        Args:
            artifact_id: The artifact identifier to register under.
            schema: The Avro schema dict to register.
            if_exists: Behaviour when the artifact already exists.
                ``"RETURN"`` (default) returns the existing artifact.
                ``"FAIL"`` raises on conflict.
                ``"RETURN_OR_UPDATE"`` returns existing or registers a new version.
                ``"UPDATE"`` always registers a new version.

        Returns:
            CachedSchema with the registered schema and registry-assigned IDs.

        Raises:
            SchemaRegistrationError: If the registry returns a 4xx or 5xx response.
            RegistryConnectionError: If the registry is unreachable.
            RuntimeError: If the client has been closed.
        """
        self._check_closed()
        async with self._lock:
            try:
                response = await self._http_client.post(
                    self._register_endpoint(),
                    json=schema,
                    headers={
                        "X-Registry-ArtifactId": artifact_id,
                        "X-Registry-ArtifactType": "AVRO",
                    },
                    params={"ifExists": if_exists},
                )
            except httpx.TransportError as exc:
                raise RegistryConnectionError(self.url, exc) from exc

            cached = self._process_registration_response(response, artifact_id, schema)
            self._schema_cache[(self.group_id, artifact_id)] = cached
            return cached

    async def _get_schema_by_id(self, id_type: str, id_value: int) -> dict[str, Any]:
        """Shared implementation for async ID-based schema lookups."""
        self._check_closed()
        cache_key = (id_type, id_value)
        if cache_key in self._id_cache:
            return self._id_cache[cache_key]

        async with self._lock:
            if cache_key in self._id_cache:
                return self._id_cache[cache_key]

            try:
                response = await self._http_client.get(
                    self._id_endpoint(id_type, id_value)
                )
            except httpx.TransportError as exc:
                raise RegistryConnectionError(self.url, exc) from exc

            schema = self._process_id_response(response, id_type, id_value)
            self._id_cache[cache_key] = schema
            return schema

    async def aclose(self) -> None:
        """Close the underlying HTTP connection pool.

        Call this when the client is no longer needed and you are not
        using it as an async context manager. Safe to call multiple times.
        """
        self._closed = True
        await self._http_client.aclose()

    async def __aenter__(self) -> AsyncApicurioRegistryClient:
        """Enter the async context manager. Returns self."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit the async context manager. Calls aclose()."""
        await self.aclose()
