"""Async Apicurio Registry v3 HTTP client with schema caching."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx

from apicurio_serdes._client import CachedSchema
from apicurio_serdes._errors import (
    RegistryConnectionError,
    SchemaNotFoundError,
)


class AsyncApicurioRegistryClient:
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
        if not url:
            raise ValueError("url must not be empty")
        if not group_id:
            raise ValueError("group_id must not be empty")
        self.url = url
        self.group_id = group_id
        self._http_client = httpx.AsyncClient(base_url=url)
        self._schema_cache: dict[tuple[str, str], CachedSchema] = {}
        self._lock = asyncio.Lock()
        self._closed = False

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
        if self._closed:
            raise RuntimeError("client is closed")
        cache_key = (self.group_id, artifact_id)
        if cache_key in self._schema_cache:
            return self._schema_cache[cache_key]

        async with self._lock:
            if cache_key in self._schema_cache:
                return self._schema_cache[cache_key]

            endpoint = (
                f"/groups/{self.group_id}"
                f"/artifacts/{artifact_id}"
                "/versions/latest/content"
            )
            try:
                response = await self._http_client.get(endpoint)
            except httpx.ConnectError as exc:
                raise RegistryConnectionError(self.url, exc) from exc

            if response.status_code == 404:
                raise SchemaNotFoundError(self.group_id, artifact_id)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise RegistryConnectionError(self.url, exc) from exc

            schema: dict[str, Any] = json.loads(response.text)
            global_id = int(response.headers["X-Registry-GlobalId"])
            content_id = int(response.headers["X-Registry-ContentId"])

            cached = CachedSchema(
                schema=schema,
                global_id=global_id,
                content_id=content_id,
            )
            self._schema_cache[cache_key] = cached
            return cached

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
