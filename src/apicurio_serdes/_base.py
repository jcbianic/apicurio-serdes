"""Shared base for sync and async Apicurio Registry clients."""

from __future__ import annotations

import json
import random
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

import httpx

from apicurio_serdes._errors import (
    RegistryConnectionError,
    SchemaNotFoundError,
    SchemaRegistrationError,
)

# HTTP status codes that indicate a transient server-side condition safe to retry.
# 500 is excluded: ambiguous for mutations (server may have processed the request).
_RETRYABLE_STATUSES: frozenset[int] = frozenset({429, 502, 503, 504})


class _CacheCore:
    """Lock-free LRU+TTL cache core. Callers must serialise all mutating calls.

    ``OrderedDict`` keeps insertion order: oldest (LRU) at the front, most-recently
    used (MRU) at the back.  Values are stored as ``(value, expiry)`` tuples where
    ``expiry`` is a monotonic timestamp (``time.monotonic() + ttl``) or ``None``
    when no TTL is configured.

    ``peek()`` is safe to call outside a lock — it checks TTL but never mutates
    ``_store``.  ``get()`` and ``set()`` **must** be called inside the caller's
    lock because they mutate ``_store`` (LRU update and eviction).
    """

    _MISSING: object = object()

    def __init__(self, max_size: int, ttl: float | None) -> None:
        if max_size < 1:
            raise ValueError(f"cache_max_size must be >= 1, got {max_size}")
        if ttl is not None and ttl <= 0:
            raise ValueError(f"cache_ttl_seconds must be > 0, got {ttl}")
        self._max_size = max_size
        self._ttl = ttl
        self._store: OrderedDict[Any, tuple[Any, float | None]] = OrderedDict()

    def peek(self, key: object) -> object:
        """TTL check without LRU update — safe to call outside a lock (no mutation)."""
        raw: tuple[Any, float | None] | None = self._store.get(key)
        if raw is None:
            return self._MISSING
        value, expiry = raw
        if expiry is not None and time.monotonic() >= expiry:
            return self._MISSING  # expired; do NOT delete — deletion requires lock
        return value

    def get(self, key: object) -> object:
        """Full LRU update + TTL eviction. Must be called inside caller's lock."""
        raw: tuple[Any, float | None] | None = self._store.get(key)
        if raw is None:
            return self._MISSING
        value, expiry = raw
        if expiry is not None and time.monotonic() >= expiry:
            del self._store[key]
            return self._MISSING
        self._store.move_to_end(key)  # bump to MRU position
        return value

    def set(self, key: object, value: object) -> None:
        """Insert/update with LRU eviction if over cap.

        Must be called inside caller's lock.
        """
        expiry = time.monotonic() + self._ttl if self._ttl is not None else None
        if key in self._store:
            self._store[key] = (value, expiry)
            self._store.move_to_end(key)
        else:
            self._store[key] = (value, expiry)
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)  # evict LRU (front)


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
    ``__init__`` after calling ``super().__init__()``, and set
    ``self._closed = True`` inside their own ``close()`` / ``aclose()``.
    """

    def __init__(
        self,
        url: str,
        group_id: str,
        *,
        max_retries: int = 3,
        retry_backoff_ms: int = 1000,
        retry_max_backoff_ms: int = 20000,
        cache_max_size: int = 1000,
        cache_ttl_seconds: float | None = None,
    ) -> None:
        if not url:
            raise ValueError("url must not be empty")
        if not group_id:
            raise ValueError("group_id must not be empty")
        if max_retries < 0:
            raise ValueError(f"max_retries must be >= 0, got {max_retries}")
        self.url = url
        self.group_id = group_id
        self.max_retries = max_retries
        self.retry_backoff_ms = retry_backoff_ms
        self.retry_max_backoff_ms = retry_max_backoff_ms
        # Validation is delegated to _CacheCore constructor.
        self._schema_cache: _CacheCore = _CacheCore(
            max_size=cache_max_size, ttl=cache_ttl_seconds
        )
        self._id_cache: _CacheCore = _CacheCore(
            max_size=cache_max_size,
            ttl=None,  # ID entries never expire (immutable)
        )
        self._closed = False

    def _check_closed(self) -> None:
        if self._closed:
            raise RuntimeError("client is closed")

    def _schema_endpoint(self, artifact_id: str) -> str:
        return (
            f"/groups/{self.group_id}/artifacts/{artifact_id}/versions/latest/content"
        )

    @staticmethod
    def _id_endpoint(id_type: str, id_value: int) -> str:
        return f"/ids/{id_type}s/{id_value}"

    def _compute_delay(self, attempt: int) -> float:
        """Full-jitter exponential backoff in seconds.

        delay = random(0, min(retry_backoff_ms * 2^attempt, retry_max_backoff_ms))
                / 1000
        """
        cap = min(self.retry_backoff_ms * (2**attempt), self.retry_max_backoff_ms)
        return random.uniform(0, cap) / 1000.0

    def _retry_delays(self) -> Iterator[float]:
        """Yield one delay (seconds) per retry attempt, up to max_retries values."""
        for attempt in range(self.max_retries):
            yield self._compute_delay(attempt)

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
            raise ValueError(f"contentId {content_id} is outside signed 64-bit range")

        return CachedSchema(
            schema=schema,
            global_id=global_id,
            content_id=content_id,
        )

    def _register_endpoint(self) -> str:
        return f"/groups/{self.group_id}/artifacts"

    def _register_body(
        self, artifact_id: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        """Build the v3 CreateArtifact request body for artifact registration."""
        return {
            "artifactId": artifact_id,
            "artifactType": "AVRO",
            "firstVersion": {
                "content": {
                    "content": json.dumps(schema),
                    "contentType": "application/json",
                }
            },
        }

    def _process_registration_response(
        self, response: httpx.Response, artifact_id: str, schema: dict[str, Any]
    ) -> CachedSchema:
        """Parse an HTTP response from an artifact registration endpoint.

        The Apicurio Registry v3 POST endpoint returns a CreateArtifactResponse
        JSON body with globalId and contentId nested under the "version" key.
        The caller passes the schema it just submitted so the CachedSchema can be
        populated without an extra GET.

        Raises:
            SchemaRegistrationError: On any non-2xx HTTP response, or if the
                response body is missing the expected "version.globalId" /
                "version.contentId" fields.
            ValueError: If globalId/contentId exceed signed 64-bit range.
        """
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise SchemaRegistrationError(artifact_id, exc) from exc

        try:
            version = response.json()["version"]
            global_id = int(version["globalId"])
            content_id = int(version["contentId"])
        except KeyError as exc:
            raise SchemaRegistrationError(artifact_id, exc) from exc

        int64_min, int64_max = -(2**63), 2**63 - 1
        if not (int64_min <= global_id <= int64_max):
            raise ValueError(f"globalId {global_id} is outside signed 64-bit range")
        if not (int64_min <= content_id <= int64_max):
            raise ValueError(f"contentId {content_id} is outside signed 64-bit range")

        return CachedSchema(schema=schema, global_id=global_id, content_id=content_id)

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

        schema: dict[str, Any] = json.loads(response.text)
        return schema
