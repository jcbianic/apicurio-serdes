"""Unit tests for _CacheCore — lock-free LRU+TTL cache core."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from apicurio_serdes._base import _CacheCore

_MISSING = _CacheCore._MISSING


# ── Validation ──────────────────────────────────────────────────────────────


class TestValidation:
    """Constructor validation raises ValueError on bad inputs."""

    def test_max_size_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="cache_max_size must be >= 1"):
            _CacheCore(max_size=0, ttl=None)

    def test_max_size_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="cache_max_size must be >= 1"):
            _CacheCore(max_size=-1, ttl=None)

    def test_ttl_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="cache_ttl_seconds must be > 0"):
            _CacheCore(max_size=1, ttl=0)

    def test_ttl_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="cache_ttl_seconds must be > 0"):
            _CacheCore(max_size=1, ttl=-1.0)

    def test_max_size_one_no_ttl_valid(self) -> None:
        cache = _CacheCore(max_size=1, ttl=None)
        assert cache is not None

    def test_max_size_one_positive_ttl_valid(self) -> None:
        cache = _CacheCore(max_size=1, ttl=30.0)
        assert cache is not None


# ── Basic get/set ────────────────────────────────────────────────────────────


class TestBasicGetSet:
    """set then get returns the stored value; get on empty cache returns MISSING."""

    def test_get_on_empty_cache_returns_missing(self) -> None:
        cache = _CacheCore(max_size=10, ttl=None)
        assert cache.get("missing") is _MISSING

    def test_set_then_get_returns_value(self) -> None:
        cache = _CacheCore(max_size=10, ttl=None)
        cache.set("k", "v")
        assert cache.get("k") == "v"

    def test_set_then_peek_returns_value(self) -> None:
        cache = _CacheCore(max_size=10, ttl=None)
        cache.set("k", "v")
        assert cache.peek("k") == "v"

    def test_peek_on_empty_cache_returns_missing(self) -> None:
        cache = _CacheCore(max_size=10, ttl=None)
        assert cache.peek("missing") is _MISSING


# ── TTL = None (no expiry) ───────────────────────────────────────────────────


class TestNoTTL:
    """Entries with ttl=None are never expired, even after time advances."""

    def test_entry_still_valid_after_time_advance(self) -> None:
        cache = _CacheCore(max_size=10, ttl=None)
        cache.set("k", "v")
        # Simulate a huge time advance — should not matter
        with patch("apicurio_serdes._base.time") as mock_time:
            mock_time.monotonic.return_value = 999_999.0
            assert cache.get("k") == "v"

    def test_peek_still_valid_after_time_advance(self) -> None:
        cache = _CacheCore(max_size=10, ttl=None)
        cache.set("k", "v")
        with patch("apicurio_serdes._base.time") as mock_time:
            mock_time.monotonic.return_value = 999_999.0
            assert cache.peek("k") == "v"


# ── TTL > 0 (expiry) ─────────────────────────────────────────────────────────


class TestTTLExpiry:
    """Entries expire after TTL elapses; peek does not delete expired entries."""

    def test_entry_valid_before_ttl(self) -> None:
        with patch("apicurio_serdes._base.time") as mock_time:
            mock_time.monotonic.return_value = 100.0
            cache = _CacheCore(max_size=10, ttl=60.0)
            cache.set("k", "v")
            # Still within TTL window
            mock_time.monotonic.return_value = 155.0
            assert cache.get("k") == "v"

    def test_peek_valid_before_ttl(self) -> None:
        with patch("apicurio_serdes._base.time") as mock_time:
            mock_time.monotonic.return_value = 100.0
            cache = _CacheCore(max_size=10, ttl=60.0)
            cache.set("k", "v")
            mock_time.monotonic.return_value = 155.0
            assert cache.peek("k") == "v"

    def test_get_returns_missing_after_ttl(self) -> None:
        with patch("apicurio_serdes._base.time") as mock_time:
            mock_time.monotonic.return_value = 100.0
            cache = _CacheCore(max_size=10, ttl=60.0)
            cache.set("k", "v")
            # TTL elapsed (expiry = 160.0)
            mock_time.monotonic.return_value = 160.0
            assert cache.get("k") is _MISSING

    def test_get_deletes_entry_after_ttl(self) -> None:
        with patch("apicurio_serdes._base.time") as mock_time:
            mock_time.monotonic.return_value = 100.0
            cache = _CacheCore(max_size=10, ttl=60.0)
            cache.set("k", "v")
            mock_time.monotonic.return_value = 160.0
            cache.get("k")  # triggers deletion
            # Entry must no longer exist in internal store
            assert "k" not in cache._store

    def test_peek_returns_missing_after_ttl(self) -> None:
        with patch("apicurio_serdes._base.time") as mock_time:
            mock_time.monotonic.return_value = 100.0
            cache = _CacheCore(max_size=10, ttl=60.0)
            cache.set("k", "v")
            mock_time.monotonic.return_value = 160.0
            assert cache.peek("k") is _MISSING

    def test_peek_does_not_delete_expired_entry(self) -> None:
        """peek must not mutate _store — deletion requires a lock."""
        with patch("apicurio_serdes._base.time") as mock_time:
            mock_time.monotonic.return_value = 100.0
            cache = _CacheCore(max_size=10, ttl=60.0)
            cache.set("k", "v")
            mock_time.monotonic.return_value = 160.0
            cache.peek("k")  # should NOT delete
            # Entry still in store (not yet deleted)
            assert "k" in cache._store

    def test_set_resets_expiry(self) -> None:
        with patch("apicurio_serdes._base.time") as mock_time:
            mock_time.monotonic.return_value = 100.0
            cache = _CacheCore(max_size=10, ttl=60.0)
            cache.set("k", "v1")
            # Advance close to expiry
            mock_time.monotonic.return_value = 155.0
            # Overwrite — new expiry = 155 + 60 = 215
            cache.set("k", "v2")
            # Advance past original expiry (160) but before new expiry
            mock_time.monotonic.return_value = 200.0
            assert cache.get("k") == "v2"


# ── LRU eviction ─────────────────────────────────────────────────────────────


class TestLRUEviction:
    """LRU eviction removes the least-recently-used entry when over capacity."""

    def test_oldest_evicted_on_overflow(self) -> None:
        cache = _CacheCore(max_size=2, ttl=None)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        # "a" was LRU — must be evicted
        assert cache.get("a") is _MISSING
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_get_promotes_entry_to_mru(self) -> None:
        """Accessing "a" via get() makes "b" the LRU; inserting "c" evicts "b"."""
        cache = _CacheCore(max_size=2, ttl=None)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.get("a")  # promotes "a" to MRU; "b" is now LRU
        cache.set("c", 3)
        assert cache.get("b") is _MISSING
        assert cache.get("a") == 1
        assert cache.get("c") == 3

    def test_peek_does_not_promote_entry(self) -> None:
        """peek() must not update LRU order; "a" should still be evicted."""
        cache = _CacheCore(max_size=2, ttl=None)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.peek("a")  # must NOT promote "a"
        cache.set("c", 3)
        # "a" is still LRU (peek didn't move it) → evicted
        assert cache.get("a") is _MISSING
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_overwrite_does_not_evict(self) -> None:
        """Updating an existing key doesn't increase size — no eviction."""
        cache = _CacheCore(max_size=2, ttl=None)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("a", "new")  # overwrite — size stays at 2
        assert cache.get("a") == "new"
        assert cache.get("b") == 2
