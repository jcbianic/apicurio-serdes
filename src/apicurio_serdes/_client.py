"""Apicurio Registry v3 HTTP client with schema caching."""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING, Any

import httpx

from apicurio_serdes._base import (
    _RETRYABLE_STATUSES,
    CachedSchema,
    _CacheCore,
    _RegistryClientBase,
)
from apicurio_serdes._errors import RegistryConnectionError

if TYPE_CHECKING:
    from typing import Literal

# Re-export so ``from apicurio_serdes._client import CachedSchema`` keeps working.
__all__ = ["ApicurioRegistryClient", "CachedSchema"]


class ApicurioRegistryClient(_RegistryClientBase):
    """HTTP client for the Apicurio Registry v3 native API.

    Handles schema retrieval by group_id / artifact_id with
    built-in caching and automatic retry on transient failures.
    Thread-safe for read operations.

    Args:
        url: Base URL of the Apicurio Registry v3 API.
             Example: ``"http://registry:8080/apis/registry/v3"``.
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
        http_client: Optional pre-configured ``httpx.Client`` to use for
                     all HTTP requests. When provided, the client is used
                     as-is and will **not** be closed by :meth:`close`.
                     Use this to configure custom timeouts, proxies, mTLS,
                     or transport-level retry. When ``None`` (default), a
                     new ``httpx.Client`` is created and managed internally.
        auth: Optional httpx-compatible authentication handler (e.g.
              ``BearerAuth``). Ignored when ``http_client`` is provided.
        cache_max_size: Maximum number of entries in each cache (LRU eviction).
                        Applies to both the schema cache and the ID cache.
                        Defaults to 1000.
        cache_ttl_seconds: Optional TTL in seconds for artifact-based schema
                           cache entries (``get_schema``, ``register_schema``).
                           ID-based lookups (``get_schema_by_global_id``,
                           ``get_schema_by_content_id``) are content-addressed
                           and never expire. Defaults to ``None`` (no expiry).

    Raises:
        ValueError: If *url* or *group_id* is empty, *max_retries* < 0,
                    *cache_max_size* < 1, or *cache_ttl_seconds* <= 0.

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
        self,
        url: str,
        group_id: str,
        *,
        max_retries: int = 3,
        retry_backoff_ms: int = 1000,
        retry_max_backoff_ms: int = 20000,
        http_client: httpx.Client | None = None,
        auth: Any = None,
        cache_max_size: int = 1000,
        cache_ttl_seconds: float | None = None,
    ) -> None:
        super().__init__(
            url,
            group_id,
            max_retries=max_retries,
            retry_backoff_ms=retry_backoff_ms,
            retry_max_backoff_ms=retry_max_backoff_ms,
            cache_max_size=cache_max_size,
            cache_ttl_seconds=cache_ttl_seconds,
        )
        self._owns_http_client = http_client is None
        self._http_client = (
            http_client
            if http_client is not None
            else httpx.Client(base_url=url, auth=auth)
        )
        self._lock = threading.RLock()

    def _http_request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Execute an HTTP request with retry on transient failures.

        Retries on ``httpx.TransportError`` and on responses with status
        codes in ``_RETRYABLE_STATUSES`` (429, 502, 503, 504).
        Uses exponential backoff with full jitter between attempts.
        """
        delays = self._retry_delays()
        while True:
            try:
                response = self._http_client.request(method, url, **kwargs)
            except httpx.TransportError as exc:
                delay = next(delays, None)
                if delay is None:
                    raise RegistryConnectionError(self.url, exc) from exc
                time.sleep(delay)
                continue
            if response.status_code in _RETRYABLE_STATUSES:
                delay = next(delays, None)
                if delay is not None:
                    time.sleep(delay)
                    continue
            return response

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
            RegistryConnectionError: If the registry is unreachable or returns
                a persistent error after all retries are exhausted.
            RuntimeError: If the client has been closed.
        """
        self._check_closed()
        cache_key = (self.group_id, artifact_id)
        cached = self._schema_cache.peek(cache_key)
        if cached is not _CacheCore._MISSING:
            return cached  # type: ignore[return-value]

        with self._lock:
            # Double-check after acquiring the lock (NFR-001)
            cached = self._schema_cache.get(cache_key)
            if cached is not _CacheCore._MISSING:
                return cached  # type: ignore[return-value]

            response = self._http_request("GET", self._schema_endpoint(artifact_id))
            cached = self._process_schema_response(response, artifact_id)
            self._schema_cache.set(cache_key, cached)
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

    def register_schema(
        self,
        artifact_id: str,
        schema: dict[str, Any],
        if_exists: Literal[
            "FAIL", "CREATE_VERSION", "FIND_OR_CREATE_VERSION"
        ] = "FIND_OR_CREATE_VERSION",
    ) -> CachedSchema:
        """Register a schema artifact with the registry.

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
        cached = self._schema_cache.peek(cache_key)
        if cached is not _CacheCore._MISSING:
            return cached  # type: ignore[return-value]
        with self._lock:
            cached = self._schema_cache.get(cache_key)
            if cached is not _CacheCore._MISSING:
                return cached  # type: ignore[return-value]
            response = self._http_request(
                "POST",
                self._register_endpoint(),
                json=self._register_body(artifact_id, schema),
                params={"ifExists": if_exists},
            )
            cached = self._process_registration_response(response, artifact_id, schema)
            self._schema_cache.set(cache_key, cached)
            return cached

    def _get_schema_by_id(self, id_type: str, id_value: int) -> dict[str, Any]:
        """Shared implementation for ID-based schema lookups (D12)."""
        self._check_closed()
        cache_key = (id_type, id_value)
        cached = self._id_cache.peek(cache_key)
        if cached is not _CacheCore._MISSING:
            return cached  # type: ignore[return-value]

        with self._lock:
            cached = self._id_cache.get(cache_key)
            if cached is not _CacheCore._MISSING:
                return cached  # type: ignore[return-value]

            response = self._http_request("GET", self._id_endpoint(id_type, id_value))
            schema = self._process_id_response(response, id_type, id_value)
            self._id_cache.set(cache_key, schema)
            return schema

    def close(self) -> None:
        """Close the underlying HTTP connection pool.

        Call this when the client is no longer needed and you are not
        using it as a context manager. Safe to call multiple times.
        When a custom ``http_client`` was provided at construction, it
        is **not** closed — the caller retains ownership.
        """
        self._closed = True
        if self._owns_http_client:
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
