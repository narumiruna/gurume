"""Tests for cache module."""

import time

from gurume.cache import MemoryCache
from gurume.cache import cache_set
from gurume.cache import cached_get
from gurume.cache import clear_cache
from gurume.cache import generate_cache_key


class TestMemoryCache:
    """Test memory cache."""

    def test_set_and_get(self):
        cache = MemoryCache(default_ttl=60.0, max_size=100)
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"

    def test_get_nonexistent(self):
        cache = MemoryCache()
        assert cache.get("nonexistent") is None

    def test_ttl_expiration(self):
        cache = MemoryCache(default_ttl=0.1)
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"

        time.sleep(0.15)
        assert cache.get("test_key") is None

    def test_max_size_eviction(self):
        cache = MemoryCache(max_size=3)
        cache.set("key1", "value1")
        time.sleep(0.01)
        cache.set("key2", "value2")
        time.sleep(0.01)
        cache.set("key3", "value3")
        time.sleep(0.01)

        cache.set("key4", "value4")

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_clear(self):
        cache = MemoryCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.size() == 2

        cache.clear()
        assert cache.size() == 0
        assert cache.get("key1") is None


class TestCacheHelpers:
    """Test cache helper functions."""

    def test_generate_cache_key_no_params(self):
        key1 = generate_cache_key("http://example.com")
        key2 = generate_cache_key("http://example.com")
        assert key1 == key2

    def test_generate_cache_key_with_params(self):
        key1 = generate_cache_key("http://example.com", {"a": "1", "b": "2"})
        key2 = generate_cache_key("http://example.com", {"b": "2", "a": "1"})
        assert key1 == key2

    def test_cached_get_and_set(self):
        clear_cache()
        cache_set("http://example.com", {"param": "value"}, "cached_data", ttl=60.0)

        result = cached_get("http://example.com", {"param": "value"})
        assert result == "cached_data"

        clear_cache()

    def test_force_refresh(self):
        clear_cache()
        cache_set("http://example.com", None, "old_value")

        result = cached_get("http://example.com", None, force_refresh=True)
        assert result is None

        clear_cache()
