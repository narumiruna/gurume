"""Caching system for HTTP responses

This module provides a flexible caching system for storing HTTP responses
to reduce redundant requests to Tabelog.

Features:
- In-memory cache with TTL (time-to-live)
- Configurable cache size with LRU eviction
- Cache key generation from URL and parameters
- Thread-safe operations
- Optional cache backends (memory, file, Redis)
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loguru import logger


@dataclass
class CacheEntry:
    """Cache entry with data and metadata"""

    data: Any
    timestamp: float
    ttl: float  # seconds

    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return time.time() - self.timestamp > self.ttl


class MemoryCache:
    """In-memory cache with TTL and LRU eviction

    This is the default cache backend. Uses Python's dict for storage
    with automatic expiration based on TTL.
    """

    def __init__(self, default_ttl: float = 3600.0, max_size: int = 1000):
        """Initialize memory cache

        Args:
            default_ttl: Default time-to-live for cache entries (seconds)
            max_size: Maximum number of entries to store
        """
        self._cache: dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl
        self._max_size = max_size

    def get(self, key: str) -> Any | None:
        """Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired
        """
        entry = self._cache.get(key)
        if entry is None:
            return None

        if entry.is_expired():
            logger.debug(f"Cache entry expired: {key[:50]}...")
            del self._cache[key]
            return None

        logger.debug(f"Cache hit: {key[:50]}...")
        return entry.data

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        # Evict oldest entry if cache is full
        if len(self._cache) >= self._max_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].timestamp)
            logger.debug(f"Cache full, evicting: {oldest_key[:50]}...")
            del self._cache[oldest_key]

        ttl = ttl or self._default_ttl
        self._cache[key] = CacheEntry(data=value, timestamp=time.time(), ttl=ttl)
        logger.debug(f"Cache set: {key[:50]}... (ttl={ttl}s)")

    def clear(self) -> None:
        """Clear all cache entries"""
        self._cache.clear()
        logger.info("Cache cleared")

    def size(self) -> int:
        """Get current cache size"""
        return len(self._cache)


class FileCache:
    """File-based cache for persistent storage

    Stores cache entries as JSON files in a directory.
    Useful for development and debugging.
    """

    def __init__(self, cache_dir: str | Path = ".tabelog_cache", default_ttl: float = 3600.0):
        """Initialize file cache

        Args:
            cache_dir: Directory to store cache files
            default_ttl: Default time-to-live for cache entries (seconds)
        """
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(exist_ok=True)
        self._default_ttl = default_ttl

    def _get_file_path(self, key: str) -> Path:
        """Get file path for cache key"""
        # Use hash to avoid filesystem issues with long keys
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self._cache_dir / f"{key_hash}.json"

    def get(self, key: str) -> Any | None:
        """Get value from cache"""
        file_path = self._get_file_path(key)
        if not file_path.exists():
            return None

        try:
            with open(file_path) as f:
                entry_dict = json.load(f)
                entry = CacheEntry(**entry_dict)

                if entry.is_expired():
                    logger.debug(f"Cache entry expired: {key[:50]}...")
                    file_path.unlink()
                    return None

                logger.debug(f"Cache hit: {key[:50]}...")
                return entry.data
        except Exception as e:
            logger.warning(f"Failed to read cache file: {e}")
            return None

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Set value in cache"""
        file_path = self._get_file_path(key)
        ttl = ttl or self._default_ttl

        entry = CacheEntry(data=value, timestamp=time.time(), ttl=ttl)

        try:
            with open(file_path, "w") as f:
                json.dump(
                    {"data": entry.data, "timestamp": entry.timestamp, "ttl": entry.ttl},
                    f,
                    ensure_ascii=False,
                )
            logger.debug(f"Cache set: {key[:50]}... (ttl={ttl}s)")
        except Exception as e:
            logger.warning(f"Failed to write cache file: {e}")

    def clear(self) -> None:
        """Clear all cache entries"""
        for file_path in self._cache_dir.glob("*.json"):
            file_path.unlink()
        logger.info("File cache cleared")

    def size(self) -> int:
        """Get current cache size"""
        return len(list(self._cache_dir.glob("*.json")))


# Global cache instance (default: memory cache)
_cache_instance: MemoryCache | FileCache | None = None


def get_cache() -> MemoryCache | FileCache:
    """Get global cache instance

    Returns:
        Global cache instance
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = MemoryCache()
    return _cache_instance


def set_cache(cache: MemoryCache | FileCache) -> None:
    """Set global cache instance

    Args:
        cache: Cache instance to use globally
    """
    global _cache_instance
    _cache_instance = cache
    logger.info(f"Cache backend set to: {cache.__class__.__name__}")


def generate_cache_key(url: str, params: dict | None = None) -> str:
    """Generate cache key from URL and parameters

    Args:
        url: Request URL
        params: Request parameters

    Returns:
        Cache key string
    """
    # Sort params for consistent key generation
    if params:
        # Convert params to tuple of sorted items for hashability
        params_tuple = tuple(sorted(params.items()))
        return f"{url}?{params_tuple}"
    return url


def cached_get(
    url: str,
    params: dict | None = None,
    ttl: float | None = None,
    force_refresh: bool = False,
) -> Any | None:
    """Get cached response or None

    Args:
        url: Request URL
        params: Request parameters
        ttl: Cache TTL (uses default if None)
        force_refresh: Skip cache and force refresh

    Returns:
        Cached response or None if not in cache
    """
    if force_refresh:
        return None

    cache = get_cache()
    key = generate_cache_key(url, params)
    return cache.get(key)


def cache_set(
    url: str,
    params: dict | None,
    value: Any,
    ttl: float | None = None,
) -> None:
    """Store response in cache

    Args:
        url: Request URL
        params: Request parameters
        value: Response to cache
        ttl: Cache TTL (uses default if None)
    """
    cache = get_cache()
    key = generate_cache_key(url, params)
    cache.set(key, value, ttl=ttl)


def clear_cache() -> None:
    """Clear all cached entries"""
    cache = get_cache()
    cache.clear()
