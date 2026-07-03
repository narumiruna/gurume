"""Small in-memory TTL cache for HTTP responses."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with data and metadata."""

    data: Any
    timestamp: float
    ttl: float

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() - self.timestamp > self.ttl


class MemoryCache:
    """In-memory cache with TTL and oldest-entry eviction."""

    def __init__(self, default_ttl: float = 3600.0, max_size: int = 1000):
        self._cache: dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl
        self._max_size = max_size

    def get(self, key: str) -> Any | None:
        """Get cached value, or None when absent or expired."""
        entry = self._cache.get(key)
        if entry is None:
            return None

        if entry.is_expired():
            logger.debug("Cache entry expired: %s...", key[:50])
            del self._cache[key]
            return None

        logger.debug("Cache hit: %s...", key[:50])
        return entry.data

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Set a cached value."""
        if self._max_size <= 0:
            return

        if len(self._cache) >= self._max_size and key not in self._cache:
            oldest_key = min(self._cache, key=lambda k: self._cache[k].timestamp)
            logger.debug("Cache full, evicting: %s...", oldest_key[:50])
            del self._cache[oldest_key]

        effective_ttl = ttl or self._default_ttl
        self._cache[key] = CacheEntry(data=value, timestamp=time.time(), ttl=effective_ttl)
        logger.debug("Cache set: %s... (ttl=%ss)", key[:50], effective_ttl)

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        logger.info("Cache cleared")

    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)


_cache_instance = MemoryCache()


def get_cache() -> MemoryCache:
    """Get the global cache instance."""
    return _cache_instance


def generate_cache_key(url: str, params: dict | None = None) -> str:
    """Generate a stable cache key from URL and query parameters."""
    if params:
        return f"{url}?{tuple(sorted(params.items()))}"
    return url


def cached_get(
    url: str,
    params: dict | None = None,
    ttl: float | None = None,
    force_refresh: bool = False,
) -> Any | None:
    """Get cached response text or None."""
    _ = ttl  # kept for the existing call signature; cache TTL is applied on set.
    if force_refresh:
        return None
    return get_cache().get(generate_cache_key(url, params))


def cache_set(
    url: str,
    params: dict | None,
    value: Any,
    ttl: float | None = None,
) -> None:
    """Store response text in the global cache."""
    get_cache().set(generate_cache_key(url, params), value, ttl=ttl)


def clear_cache() -> None:
    """Clear all cached entries."""
    get_cache().clear()
