"""
Unit Tests for CacheService (src/services/cache_service.py).

Covers:
- cache miss (returns None)
- cache hit (returns deserialized object)
- JSON serialization and deserialization
- TTL passed correctly (POSTS_LIST_TTL=60, POST_ITEM_TTL=300, None)
- delete operation
- pattern deletion (delete_by_pattern)
- invalidate post list (invalidate_post_list)
- invalidate individual post (invalidate_post)
- Redis GET failure fails open (returns None, no crash)
- Redis SET failure fails open (returns False, no crash)
- Redis DELETE failure fails open (returns False, no crash)
- Redis pattern deletion failure fails open (returns False, no crash)
- Return value semantics for invalidate_post when underlying ops fail
- Cache key builder static methods
"""

from unittest.mock import AsyncMock
import pytest

from src.services.cache_service import (
    CacheService,
    POSTS_LIST_TTL,
    POST_ITEM_TTL,
)


@pytest.mark.asyncio
async def test_cache_miss(fake_cache_service):
    """Retrieving a non-existent key returns None."""
    result = await fake_cache_service.get("nonexistent:key")
    assert result is None


@pytest.mark.asyncio
async def test_cache_hit_and_json_serialization(fake_cache_service):
    """Storing a dict serializes to JSON and deserializes back into a dict on hit."""
    sample_payload = {
        "id": 1,
        "title": "Cached Post",
        "tags": ["tech", "api"],
        "views": 42,
    }
    set_success = await fake_cache_service.set("posts:item:1", sample_payload)
    assert set_success is True

    cached_val = await fake_cache_service.get("posts:item:1")
    assert cached_val == sample_payload
    assert cached_val["title"] == "Cached Post"
    assert cached_val["tags"] == ["tech", "api"]


@pytest.mark.asyncio
async def test_ttl_passed_correctly(fake_redis, fake_cache_service):
    """TTL parameters set proper expiration for list and item policies."""
    # List TTL: 60s
    await fake_cache_service.set("posts:list:1", {"items": []}, ttl=POSTS_LIST_TTL)
    list_ttl = await fake_redis.ttl("posts:list:1")
    assert 0 < list_ttl <= 60

    # Item TTL: 300s
    await fake_cache_service.set("posts:item:1", {"title": "Test"}, ttl=POST_ITEM_TTL)
    item_ttl = await fake_redis.ttl("posts:item:1")
    assert 60 < item_ttl <= 300

    # No TTL: key persists without expiration
    await fake_cache_service.set("posts:eternal", {"forever": True}, ttl=None)
    eternal_ttl = await fake_redis.ttl("posts:eternal")
    assert eternal_ttl == -1


@pytest.mark.asyncio
async def test_cache_delete(fake_cache_service):
    """Delete removes the key and subsequent get returns None."""
    await fake_cache_service.set("temp:key", "val")
    assert await fake_cache_service.get("temp:key") == "val"

    deleted = await fake_cache_service.delete("temp:key")
    assert deleted is True
    assert await fake_cache_service.get("temp:key") is None


@pytest.mark.asyncio
async def test_delete_by_pattern(fake_cache_service):
    """delete_by_pattern removes all matching keys while preserving other keys."""
    await fake_cache_service.set("posts:list:page:1:limit:10", {"page": 1})
    await fake_cache_service.set("posts:list:page:2:limit:10", {"page": 2})
    await fake_cache_service.set("posts:item:42", {"title": "Stay"})

    res = await fake_cache_service.delete_by_pattern("posts:list:*")
    assert res is True

    assert await fake_cache_service.get("posts:list:page:1:limit:10") is None
    assert await fake_cache_service.get("posts:list:page:2:limit:10") is None
    assert await fake_cache_service.get("posts:item:42") == {"title": "Stay"}


@pytest.mark.asyncio
async def test_invalidate_post_list(fake_cache_service):
    """invalidate_post_list removes all posts:list:* keys."""
    await fake_cache_service.set("posts:list:page:1:limit:10", {"p": 1})
    await fake_cache_service.set("posts:item:1", {"title": "Keep"})

    success = await fake_cache_service.invalidate_post_list()
    assert success is True

    assert await fake_cache_service.get("posts:list:page:1:limit:10") is None
    assert await fake_cache_service.get("posts:item:1") is not None


@pytest.mark.asyncio
async def test_invalidate_individual_post_success(fake_cache_service):
    """invalidate_post clears both the specific item and all list caches, returning True."""
    await fake_cache_service.set("posts:item:7", {"title": "Post 7"})
    await fake_cache_service.set("posts:item:8", {"title": "Post 8"})
    await fake_cache_service.set("posts:list:page:1:limit:10", {"items": [7, 8]})

    res = await fake_cache_service.invalidate_post(7)
    assert res is True

    assert await fake_cache_service.get("posts:item:7") is None
    assert await fake_cache_service.get("posts:item:8") == {"title": "Post 8"}
    assert await fake_cache_service.get("posts:list:page:1:limit:10") is None


@pytest.mark.asyncio
async def test_redis_get_failure_fails_open():
    """Redis GET exception fails open: returns None and does not raise."""
    mock_redis = AsyncMock()
    mock_redis.get.side_effect = ConnectionError("Upstash Redis connection timeout")
    service = CacheService(mock_redis)

    result = await service.get("posts:item:1")
    assert result is None


@pytest.mark.asyncio
async def test_redis_set_failure_fails_open():
    """Redis SET exception fails open: returns False and does not raise."""
    mock_redis = AsyncMock()
    mock_redis.set.side_effect = TimeoutError("Upstash Redis write failed")
    service = CacheService(mock_redis)

    result = await service.set("posts:item:1", {"title": "Fail"})
    assert result is False


@pytest.mark.asyncio
async def test_redis_delete_failure_fails_open():
    """Redis DELETE exception fails open: returns False and does not raise."""
    mock_redis = AsyncMock()
    mock_redis.delete.side_effect = RuntimeError("Upstash Redis delete failed")
    service = CacheService(mock_redis)

    result = await service.delete("posts:item:1")
    assert result is False


@pytest.mark.asyncio
async def test_redis_pattern_deletion_failure_fails_open():
    """Redis pattern deletion exception fails open: returns False and does not raise."""
    mock_redis = AsyncMock()
    mock_redis.keys.side_effect = RuntimeError("Redis keys command failed")
    service = CacheService(mock_redis)

    result = await service.delete_by_pattern("posts:list:*")
    assert result is False


@pytest.mark.asyncio
async def test_invalidate_post_returns_false_on_delete_failure():
    """invalidate_post returns False when individual delete fails."""
    mock_redis = AsyncMock()
    # delete fails
    mock_redis.delete.side_effect = RuntimeError("Delete error")
    mock_redis.keys.return_value = ["posts:list:1"]
    service = CacheService(mock_redis)

    res = await service.invalidate_post(42)
    assert res is False


@pytest.mark.asyncio
async def test_invalidate_post_returns_false_on_pattern_failure():
    """invalidate_post returns False when list pattern invalidation fails."""
    mock_redis = AsyncMock()
    # item delete succeeds, but keys search for pattern fails
    mock_redis.delete.return_value = 1
    mock_redis.keys.side_effect = RuntimeError("Keys error")
    service = CacheService(mock_redis)

    res = await service.invalidate_post(42)
    assert res is False


def test_cache_key_builders():
    """Static cache key builders construct expected deterministic key patterns."""
    assert CacheService.build_posts_list_key(1, 10) == "posts:list:page:1:limit:10"
    assert CacheService.build_posts_list_key(3, 25) == "posts:list:page:3:limit:25"
    assert CacheService.build_post_item_key(99) == "posts:item:99"
    assert CacheService.build_post_item_key(1) == "posts:item:1"
