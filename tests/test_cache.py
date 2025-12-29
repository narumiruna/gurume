"""Tests for cache module"""

import time

from tabelog.cache import FileCache
from tabelog.cache import MemoryCache
from tabelog.cache import cache_set
from tabelog.cache import cached_get
from tabelog.cache import clear_cache
from tabelog.cache import generate_cache_key
from tabelog.cache import set_cache


class TestMemoryCache:
    """Test memory cache"""

    def test_set_and_get(self):
        """Test basic set and get operations"""
        cache = MemoryCache(default_ttl=60.0, max_size=100)
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"

    def test_get_nonexistent(self):
        """Test getting nonexistent key returns None"""
        cache = MemoryCache()
        assert cache.get("nonexistent") is None

    def test_ttl_expiration(self):
        """Test cache entry expires after TTL"""
        cache = MemoryCache(default_ttl=0.1)  # 0.1 second TTL
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"

        # Wait for expiration
        time.sleep(0.15)
        assert cache.get("test_key") is None

    def test_max_size_eviction(self):
        """Test oldest entry is evicted when cache is full"""
        cache = MemoryCache(max_size=3)
        cache.set("key1", "value1")
        time.sleep(0.01)  # Ensure different timestamps
        cache.set("key2", "value2")
        time.sleep(0.01)
        cache.set("key3", "value3")
        time.sleep(0.01)

        # Cache is full, adding new entry should evict oldest (key1)
        cache.set("key4", "value4")

        assert cache.get("key1") is None  # Evicted
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_clear(self):
        """Test clearing cache"""
        cache = MemoryCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.size() == 2

        cache.clear()
        assert cache.size() == 0
        assert cache.get("key1") is None


class TestFileCache:
    """Test file cache"""

    def test_set_and_get(self, tmp_path):
        """Test basic set and get operations"""
        cache = FileCache(cache_dir=tmp_path, default_ttl=60.0)
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"

    def test_get_nonexistent(self, tmp_path):
        """Test getting nonexistent key returns None"""
        cache = FileCache(cache_dir=tmp_path)
        assert cache.get("nonexistent") is None

    def test_clear(self, tmp_path):
        """Test clearing cache"""
        cache = FileCache(cache_dir=tmp_path)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.size() == 2

        cache.clear()
        assert cache.size() == 0


class TestCacheHelpers:
    """Test cache helper functions"""

    def test_generate_cache_key_no_params(self):
        """Test cache key generation without params"""
        key1 = generate_cache_key("http://example.com")
        key2 = generate_cache_key("http://example.com")
        assert key1 == key2

    def test_generate_cache_key_with_params(self):
        """Test cache key generation with params"""
        key1 = generate_cache_key("http://example.com", {"a": "1", "b": "2"})
        key2 = generate_cache_key("http://example.com", {"b": "2", "a": "1"})
        # Order shouldn't matter
        assert key1 == key2

    def test_cached_get_and_set(self):
        """Test global cache get and set"""
        # Reset to memory cache
        set_cache(MemoryCache())

        # Set value
        cache_set("http://example.com", {"param": "value"}, "cached_data", ttl=60.0)

        # Get value
        result = cached_get("http://example.com", {"param": "value"})
        assert result == "cached_data"

        # Clear cache for next test
        clear_cache()

    def test_force_refresh(self):
        """Test force refresh bypasses cache"""
        set_cache(MemoryCache())
        cache_set("http://example.com", None, "old_value")

        # Force refresh should return None
        result = cached_get("http://example.com", None, force_refresh=True)
        assert result is None

        clear_cache()
