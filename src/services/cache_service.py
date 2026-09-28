"""
Cache Service

Encapsulates Redis cache operations with JSON serialization/deserialization.
Provides clean async helpers for get, set, delete, and pattern invalidation.

All methods handle Redis failures gracefully:
  - GET failure → returns None (triggers a cache MISS, falls back to PostgreSQL)
  - SET failure → logs the error, does not block the response
  - DELETE failure → logs the error silently
  - Invalidation failure → logs the error silently

This ensures a Redis outage does not destroy the core API.

Step 9 Enhancements:
  - TTL (Time-To-Live) support on set() (default: 300 seconds / 5 minutes)
  - Pattern-based cache invalidation (delete_by_pattern)
  - Specific post invalidation helper (invalidate_post)
"""

import json
import logging
from typing import Any, Optional
from upstash_redis.asyncio import Redis

logger = logging.getLogger(__name__)

# Default Time-To-Live for cached entries (5 minutes = 300 seconds)
DEFAULT_CACHE_TTL = 300


class CacheService:
    """
    A thin wrapper around the Upstash Redis async client that handles
    JSON serialization, TTL expirations, pattern invalidations, and
    graceful error handling for cache operations.
    """

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a cached value by key.

        Returns the deserialized Python object if found, or None on
        cache miss or Redis failure.

        Verified SDK behavior: redis.get() returns a string (the raw
        value stored) or None. We json.loads() to recover the original
        Python object.
        """
        try:
            value = await self.redis.get(key)
            if value is None:
                return None

            return json.loads(value)

        except Exception as e:
            logger.error("Redis GET failed for key '%s': %s", key, str(e))
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = DEFAULT_CACHE_TTL
    ) -> bool:
        """
        Store a value in the cache as a JSON string with an optional TTL (in seconds).

        Parameters:
            key: The Redis key.
            value: The Python object to store.
            ttl: Time-To-Live in seconds (default: 300s). If None, key will not expire.

        Returns True on success, False on failure.
        """
        try:
            json_value = json.dumps(value, default=str)
            if ttl is not None and ttl > 0:
                await self.redis.set(key, json_value, ex=ttl)
            else:
                await self.redis.set(key, json_value)
            return True

        except Exception as e:
            logger.error("Redis SET failed for key '%s': %s", key, str(e))
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete a cached value by key.

        Returns True on success, False on failure.
        """
        try:
            await self.redis.delete(key)
            return True

        except Exception as e:
            logger.error("Redis DELETE failed for key '%s': %s", key, str(e))
            return False

    async def delete_by_pattern(self, pattern: str) -> bool:
        """
        Find and delete all keys matching a given wildcard pattern (e.g. 'posts:list:*').

        Uses redis.keys(pattern) to retrieve matching keys and redis.delete(*keys)
        to remove them.

        Returns True on success, False on failure.
        """
        try:
            matching_keys = await self.redis.keys(pattern)
            if matching_keys and isinstance(matching_keys, list) and len(matching_keys) > 0:
                await self.redis.delete(*matching_keys)
                logger.info("Invalidated %d cache keys matching pattern '%s'", len(matching_keys), pattern)
            return True

        except Exception as e:
            logger.error("Redis pattern invalidation failed for '%s': %s", pattern, str(e))
            return False

    async def invalidate_post_list(self) -> bool:
        """
        Invalidate all paginated post list cache entries ('posts:list:*').
        Called when a post is created, updated, or deleted.
        """
        return await self.delete_by_pattern("posts:list:*")

    async def invalidate_post(self, post_id: int) -> bool:
        """
        Invalidate both the individual post cache ('posts:item:{post_id}')
        and all paginated post list caches ('posts:list:*').
        Called when a post is updated or deleted.
        """
        item_key = self.build_post_item_key(post_id)
        await self.delete(item_key)
        await self.invalidate_post_list()
        return True

    # ----------------------------------------------------------------
    # Cache key builders
    # ----------------------------------------------------------------

    @staticmethod
    def build_posts_list_key(page: int, limit: int) -> str:
        """
        Build a deterministic cache key for a paginated post list.

        Pattern: posts:list:page:{page}:limit:{limit}
        Example: posts:list:page:1:limit:10
        """
        return f"posts:list:page:{page}:limit:{limit}"

    @staticmethod
    def build_post_item_key(post_id: int) -> str:
        """
        Build a deterministic cache key for an individual post.

        Pattern: posts:item:{post_id}
        Example: posts:item:42
        """
        return f"posts:item:{post_id}"
