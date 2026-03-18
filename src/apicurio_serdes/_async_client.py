"""Async Apicurio Registry v3 HTTP client with schema caching."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import httpx

from apicurio_serdes._base import CachedSchema, _RETRYABLE_STATUSES, _RegistryClientBase
from apicurio_serdes._errors import RegistryConnectionError

if TYPE_CHECKING:
    from typing import Literal


class AsyncApicurioRegistryClient(_RegistryClientBase):
    """Async HTTP client for the Apicurio Registry v3 native API.

    Non-blocking counterpart to ApicurioRegistryClient. Uses
    httpx.AsyncClient for async I/O. Safe for concurrent use
    from multiple coroutines within the same event loop. Includes
    automatic retry on transient failures.

    Args:
        url: Base URL of the Apicurio Registry v3 API.
             Example: "http://registry:8080/apis/registry/v3"
        group_id: Schema group identifier. Applied to every
                  schema lookup made by this client instance.
        max_retries: Maximum number of retry attempts on transient
                     failures (transport errors and HTTP 429/502/503/504).
                     Defaults to 3. Set to 0 to disable retries.
        retry_backoff_ms: Base backoff delay in milliseconds for the first
                          retry. Subsequent retries use exponential backoff
                          with full jitter. Defaults to 1000.
        retry_max_backoff_ms: Maximum backoff delay cap in milliseconds.
                              Defaults to 20000.
        http_client: Optional pre-configured ``httpx.AsyncClient`` to use
                     for all HTTP requests. When provided, the client is
                     used as-is and will **not** be closed by :meth:`aclose`.
                     When ``None`` (default), a new ``httpx.AsyncClient`` is
                     created and managed internally.
        auth: Optional httpx-compatible authentication handler. Ignored
              when ``http_client`` is provided.

    Raises:
        ValueError: If url or group_id is empty, or max_retries < 0.
    """

    def __init__(
        self,
        url: str,
        group_id: str,
        *,
        max_retries: int = 3,
        retry_backoff_ms: int = 1000,
        retry_max_backoff_ms: int = 20000,
        http_client: httpx.AsyncClient | None = None,
        auth: Any = None,
    ) -> None:
        super().__init__(
            url,
            group_id,
            max_retries=max_retries,
            retry_backoff_ms=retry_backoff_ms,
            retry_max_backoff_ms=retry_max_backoff_ms,
        )
        self._owns_http_client = http_client is None
        self._http_client = (
            http_client
            if http_client is not None
            else httpx.AsyncClient(base_url=url, auth=auth)
        )
        self._lock = asyncio.Lock()

    async def _http_request(
        self, method: str, url: str, **kwargs: Any
    ) -> httpx.Response:
        """Execute an HTTP request with retry on transient failures (async).

        Retries on ``httpx.TransportError`` and on responses with status
        codes in ``_RETRYABLE_STATUSES`` (429, 502, 503, 504).
        Uses exponential backoff with full jitter between attempts.
        """
        delays = self._retry_delays()
        while True:
            try:
                response = await self._http_client.request(method, url, **kwargs)
            except httpx.TransportError as exc:
                delay = next(delays, None)
                if delay is None:
                    raise RegistryConnectionError(self.url, exc) from exc
                await asyncio.sleep(delay)
                continue
            if response.status_code in _RETRYABLE_STATUSES:
                delay = next(delays, None)
                if delay is not None:
                    await asyncio.sleep(delay)
                    continue
            return response

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
                a persistent error after all retries are exhausted.
            RuntimeError: If the client has been closed.
        """
        self._check_closed()
        cache_key = (self.group_id, artifact_id)
        if cache_key in self._schema_cache:
            return self._schema_cache[cache_key]

        async with self._lock:
            if cache_key in self._schema_cache:
                return self._schema_cache[cache_key]

            response = await self._http_request(
                "GET", self._schema_endpoint(artifact_id)
            )
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
        if_exists: Literal[
            "FAIL", "CREATE_VERSION", "FIND_OR_CREATE_VERSION"
        ] = "FIND_OR_CREATE_VERSION",
    ) -> CachedSchema:
        """Register a schema artifact with the registry (async).

        Posts the schema to the registry under the configured group. On success,
        populates the internal cache so subsequent ``get_schema`` calls are cache
        hits with no additional HTTP request.

        Args:
            artifact_id: The artifact identifier to register under.
            schema: The Avro schema dict to register.
            if_exists: Behaviour when the artifact already exists.
                ``"FIND_OR_CREATE_VERSION"`` (default) returns the existing version
                if the content matches, otherwise creates a new version.
                ``"FAIL"`` raises on conflict.
                ``"CREATE_VERSION"`` always creates a new version.

        Returns:
            CachedSchema with the registered schema and registry-assigned IDs.

        Raises:
            SchemaRegistrationError: If the registry returns a 4xx or 5xx response.
            RegistryConnectionError: If the registry is unreachable.
            RuntimeError: If the client has been closed.
        """
        self._check_closed()
        cache_key = (self.group_id, artifact_id)
        if cache_key in self._schema_cache:
            return self._schema_cache[cache_key]
        async with self._lock:
            if cache_key in self._schema_cache:
                return self._schema_cache[cache_key]
            response = await self._http_request(
                "POST",
                self._register_endpoint(),
                json=self._register_body(artifact_id, schema),
                params={"ifExists": if_exists},
            )
            cached = self._process_registration_response(response, artifact_id, schema)
            self._schema_cache[cache_key] = cached
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

            response = await self._http_request(
                "GET", self._id_endpoint(id_type, id_value)
            )
            schema = self._process_id_response(response, id_type, id_value)
            self._id_cache[cache_key] = schema
            return schema

    async def aclose(self) -> None:
        """Close the underlying HTTP connection pool.

        Call this when the client is no longer needed and you are not
        using it as an async context manager. Safe to call multiple times.
        When a custom ``http_client`` was provided at construction, it
        is **not** closed — the caller retains ownership.
        """
        self._closed = True
        if self._owns_http_client:
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
