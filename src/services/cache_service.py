"""
Cache Service

Encapsulates Redis cache operations with JSON serialization/deserialization.
Provides clean async helpers for get, set, and delete operations.

All methods handle Redis failures gracefully:
  - GET failure → returns None (triggers a cache MISS, falls back to PostgreSQL)
  - SET failure → logs the error, does not block the response
  - DELETE failure → logs the error silently

This ensures a Redis outage does not destroy the core API.

SDK Behavior Notes (upstash-redis 1.8.0, verified via source inspection):
  - GET has no entry in the SDK's FORMATTERS dict, so it returns the raw
    result from the REST response. When a string was stored, GET returns
    that string. When the key doesn't exist, GET returns None.
  - SET uses _format_command which calls json.dumps() on non-string/int/float
    values. Since our data contains datetime and UUID objects that are not
    natively JSON-serializable, we pre-serialize with json.dumps(value, default=str).
  - Therefore: SET receives a plain JSON string, and GET returns that same string.
    We need json.loads() on the GET side to recover the Python dict/list.
"""

import json
import logging
from typing import Any, Optional
from upstash_redis.asyncio import Redis

logger = logging.getLogger(__name__)


class CacheService:
    """
    A thin wrapper around the Upstash Redis async client that handles
    JSON serialization and graceful error handling for cache operations.
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

    async def set(self, key: str, value: Any) -> bool:
        """
        Store a value in the cache as a JSON string.

        Returns True on success, False on failure.
        No TTL is set in Step 8 — that will be introduced in Step 9.

        We use json.dumps(value, default=str) to handle datetime and UUID
        objects that are not natively JSON-serializable. The resulting string
        is passed to redis.set(), where the SDK sends it as-is (strings pass
        through _format_command unchanged).
        """
        try:
            json_value = json.dumps(value, default=str)
            await self.redis.set(key, json_value)
            return True

        except Exception as e:
            logger.error("Redis SET failed for key '%s': %s", key, str(e))
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete a cached value by key.

        Prepared for Step 9 cache invalidation.
        Returns True on success, False on failure.
        """
        try:
            await self.redis.delete(key)
            return True

        except Exception as e:
            logger.error("Redis DELETE failed for key '%s': %s", key, str(e))
            return False

    # ----------------------------------------------------------------
    # Cache key builders
    # ----------------------------------------------------------------
    # Including pagination parameters (page and limit) in the list key
    # is critical. Without them, requesting page 2 would overwrite the
    # cached result for page 1, and every page would return the same
    # stale data. Each unique (page, limit) combination MUST map to
    # its own cache entry.
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
