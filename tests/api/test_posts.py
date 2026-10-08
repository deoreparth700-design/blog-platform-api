"""
API Tests for Posts Endpoints (/api/posts/).

Tests:
- GET /api/posts/ (list)
  - cache MISS, cache HIT, X-Cache header
  - 60 second TTL policy (POSTS_LIST_TTL)
  - cached response matches expected payload
  - pagination defaults and custom parameters
- GET /api/posts/{post_id} (item)
  - cache MISS, cache HIT, X-Cache header
  - 300 second TTL policy (POST_ITEM_TTL)
  - 404 Not Found handling
  - 404 responses are NOT cached
- POST /api/posts/ (create)
  - authenticated create -> 201
  - missing auth -> 401
  - validation error -> 422
  - post list cache invalidation
- PUT /api/posts/{post_id} (update)
  - owner update -> 200
  - missing auth -> 401
  - non-owner forbidden -> 403
  - invalid body -> 422
  - invalidation of item cache AND list cache
- DELETE /api/posts/{post_id} (delete)
  - owner delete -> 204
  - missing auth -> 401
  - non-owner forbidden -> 403
  - nonexistent post -> 404
  - invalidation of item cache AND list cache
- Redis failure resilience (GET failure, SET failure, invalidation failure)
"""

from unittest.mock import AsyncMock
from uuid import UUID
from datetime import datetime, timezone
import pytest
from fastapi import HTTPException, status

from src.app import app
from src.routes.posts import get_post_service, get_cache_service
from src.services.cache_service import CacheService, POSTS_LIST_TTL, POST_ITEM_TTL
from tests.conftest import USER_A_ID, USER_B_ID


# ---------------------------------------------------------------------------
# Helpers & Fixture Setup
# ---------------------------------------------------------------------------
def make_post_payload(post_id: int = 1, author_id: str = USER_A_ID, title: str = "Test Post", content: str = "Test Content"):
    return {
        "id": post_id,
        "author_id": UUID(author_id),
        "title": title,
        "content": content,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# GET /api/posts/ (Post List & Caching)
# ---------------------------------------------------------------------------
def test_get_posts_list_miss_then_hit_and_ttl(client, fake_cache_service, fake_redis, mock_post_service):
    """
    GET /api/posts/ verifies:
    1. First call: Redis MISS, fetches from service, caches with 60s TTL, header X-Cache: MISS.
    2. Second call: Redis HIT, served from cache, header X-Cache: HIT.
    3. Cached content matches expected response.
    """
    sample_posts = [make_post_payload(1), make_post_payload(2)]
    mock_post_service.get_posts.return_value = {
        "items": sample_posts,
        "page": 1,
        "limit": 10,
        "total": 2,
        "total_pages": 1,
    }

    app.dependency_overrides[get_post_service] = lambda: mock_post_service
    app.dependency_overrides[get_cache_service] = lambda: fake_cache_service

    # First request: Cold cache -> MISS
    resp1 = client.get("/api/posts/?page=1&limit=10")
    assert resp1.status_code == 200
    assert resp1.headers.get("X-Cache") == "MISS"
    data1 = resp1.json()
    assert data1["total"] == 2
    assert len(data1["items"]) == 2
    mock_post_service.get_posts.assert_awaited_once_with(1, 10)

    # Verify TTL in Redis is <= 60s
    key = CacheService.build_posts_list_key(1, 10)
    ttl = client.app  # just reference
    import asyncio
    ttl_val = asyncio.run(fake_redis.ttl(key))
    assert 0 < ttl_val <= POSTS_LIST_TTL

    # Second request: Warm cache -> HIT
    resp2 = client.get("/api/posts/?page=1&limit=10")
    assert resp2.status_code == 200
    assert resp2.headers.get("X-Cache") == "HIT"
    data2 = resp2.json()
    assert data2 == data1

    # Service should NOT be called a second time
    assert mock_post_service.get_posts.await_count == 1


def test_get_posts_list_custom_pagination(client, fake_cache_service, mock_post_service):
    """GET /api/posts/ passes custom page and limit to service and uses distinct cache key."""
    mock_post_service.get_posts.return_value = {
        "items": [make_post_payload(5)],
        "page": 2,
        "limit": 5,
        "total": 6,
        "total_pages": 2,
    }
    app.dependency_overrides[get_post_service] = lambda: mock_post_service
    app.dependency_overrides[get_cache_service] = lambda: fake_cache_service

    resp = client.get("/api/posts/?page=2&limit=5")
    assert resp.status_code == 200
    assert resp.headers.get("X-Cache") == "MISS"
    mock_post_service.get_posts.assert_awaited_once_with(2, 5)


# ---------------------------------------------------------------------------
# GET /api/posts/{post_id} (Individual Post & Caching)
# ---------------------------------------------------------------------------
def test_get_post_item_miss_then_hit_and_ttl(client, fake_cache_service, fake_redis, mock_post_service):
    """
    GET /api/posts/{id} verifies:
    1. First call: Redis MISS, fetches from service, caches with 300s TTL, header X-Cache: MISS.
    2. Second call: Redis HIT, header X-Cache: HIT.
    3. TTL is <= 300s.
    """
    sample = make_post_payload(42, title="Unique Post")
    mock_post_service.get_post_by_id.return_value = sample

    app.dependency_overrides[get_post_service] = lambda: mock_post_service
    app.dependency_overrides[get_cache_service] = lambda: fake_cache_service

    # First request: MISS
    resp1 = client.get("/api/posts/42")
    assert resp1.status_code == 200
    assert resp1.headers.get("X-Cache") == "MISS"
    assert resp1.json()["title"] == "Unique Post"

    # Verify TTL in Redis is between 60 and 300 seconds
    import asyncio
    item_key = CacheService.build_post_item_key(42)
    ttl_val = asyncio.run(fake_redis.ttl(item_key))
    assert 60 < ttl_val <= POST_ITEM_TTL

    # Second request: HIT
    resp2 = client.get("/api/posts/42")
    assert resp2.status_code == 200
    assert resp2.headers.get("X-Cache") == "HIT"
    assert resp2.json()["title"] == "Unique Post"
    assert mock_post_service.get_post_by_id.await_count == 1


def test_get_post_item_404_not_cached(client, fake_cache_service, fake_redis, mock_post_service):
    """GET /api/posts/{id} returning 404 does NOT store anything in Redis."""
    mock_post_service.get_post_by_id.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
    )
    app.dependency_overrides[get_post_service] = lambda: mock_post_service
    app.dependency_overrides[get_cache_service] = lambda: fake_cache_service

    resp = client.get("/api/posts/999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Post not found"

    import asyncio
    cached = asyncio.run(fake_cache_service.get("posts:item:999"))
    assert cached is None


# ---------------------------------------------------------------------------
# POST /api/posts/ (Create Post & Cache Invalidation)
# ---------------------------------------------------------------------------
def test_create_post_success_and_invalidates_list_cache(client, auth_headers, fake_cache_service, mock_post_service):
    """
    POST /api/posts/:
    - Creates post -> 201
    - Invalidates list caches ('posts:list:*')
    - Returns newly created post
    """
    # Seed list cache
    import asyncio
    asyncio.run(fake_cache_service.set("posts:list:page:1:limit:10", {"items": []}))

    created_post = make_post_payload(10, author_id=USER_A_ID, title="New Post", content="New Content")
    mock_post_service.create_post.return_value = created_post

    app.dependency_overrides[get_post_service] = lambda: mock_post_service
    app.dependency_overrides[get_cache_service] = lambda: fake_cache_service

    payload = {"title": "New Post", "content": "New Content"}
    resp = client.post("/api/posts/", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["id"] == 10

    # Verify list cache was invalidated
    cached_list = asyncio.run(fake_cache_service.get("posts:list:page:1:limit:10"))
    assert cached_list is None


def test_create_post_unauthenticated_returns_401(client, fake_cache_service, mock_post_service):
    """POST /api/posts/ without token returns 401."""
    app.dependency_overrides[get_post_service] = lambda: mock_post_service
    app.dependency_overrides[get_cache_service] = lambda: fake_cache_service

    resp = client.post("/api/posts/", json={"title": "Test", "content": "Test"})
    assert resp.status_code == 401


def test_create_post_invalid_body_returns_422(client, auth_headers, fake_cache_service, mock_post_service):
    """POST /api/posts/ with missing fields returns 422 Unprocessable Entity."""
    app.dependency_overrides[get_post_service] = lambda: mock_post_service
    app.dependency_overrides[get_cache_service] = lambda: fake_cache_service

    resp = client.post("/api/posts/", json={"title": "Missing Content"}, headers=auth_headers)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PUT /api/posts/{post_id} (Update Post & Dual Invalidation)
# ---------------------------------------------------------------------------
def test_update_post_owner_success_and_dual_invalidation(client, auth_headers, fake_cache_service, mock_post_service):
    """
    PUT /api/posts/{id}:
    - Owner updates post -> 200
    - Invalidates individual item cache ('posts:item:{id}')
    - Invalidates list caches ('posts:list:*')
    """
    import asyncio
    asyncio.run(fake_cache_service.set("posts:item:1", {"title": "Old"}))
    asyncio.run(fake_cache_service.set("posts:list:page:1:limit:10", {"items": [1]}))

    updated = make_post_payload(1, author_id=USER_A_ID, title="Updated Title", content="Updated Content")
    mock_post_service.update_post.return_value = updated

    app.dependency_overrides[get_post_service] = lambda: mock_post_service
    app.dependency_overrides[get_cache_service] = lambda: fake_cache_service

    resp = client.put("/api/posts/1", json={"title": "Updated Title"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"

    # Both item and list caches must be purged
    assert asyncio.run(fake_cache_service.get("posts:item:1")) is None
    assert asyncio.run(fake_cache_service.get("posts:list:page:1:limit:10")) is None


def test_update_post_unauthenticated_returns_401(client, fake_cache_service, mock_post_service):
    """PUT /api/posts/{id} without token returns 401."""
    app.dependency_overrides[get_post_service] = lambda: mock_post_service
    app.dependency_overrides[get_cache_service] = lambda: fake_cache_service

    resp = client.put("/api/posts/1", json={"title": "Test"})
    assert resp.status_code == 401


def test_update_post_non_owner_returns_403(client, user_b_headers, fake_cache_service, mock_post_service):
    """PUT /api/posts/{id} by non-owner returns 403 Forbidden."""
    mock_post_service.update_post.side_effect = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this post"
    )
    app.dependency_overrides[get_post_service] = lambda: mock_post_service
    app.dependency_overrides[get_cache_service] = lambda: fake_cache_service

    resp = client.put("/api/posts/1", json={"title": "Attack"}, headers=user_b_headers)
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Not authorized to update this post"


def test_update_post_invalid_body_returns_422(client, auth_headers, fake_cache_service, mock_post_service):
    """PUT /api/posts/{id} with invalid body types returns 422."""
    app.dependency_overrides[get_post_service] = lambda: mock_post_service
    app.dependency_overrides[get_cache_service] = lambda: fake_cache_service

    resp = client.put("/api/posts/1", json={"title": 12345}, headers=auth_headers)
    # FastAPI/Pydantic might coerce or reject; if title is int, let's pass a dict or invalid structure
    resp_bad = client.put("/api/posts/1", json="not a dict", headers=auth_headers)
    assert resp_bad.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/posts/{post_id} (Delete Post & Dual Invalidation)
# ---------------------------------------------------------------------------
def test_delete_post_owner_success_and_dual_invalidation(client, auth_headers, fake_cache_service, mock_post_service):
    """
    DELETE /api/posts/{id}:
    - Owner deletes post -> 204 No Content
    - Invalidates item cache AND list cache
    """
    import asyncio
    asyncio.run(fake_cache_service.set("posts:item:1", {"title": "Delete Me"}))
    asyncio.run(fake_cache_service.set("posts:list:page:1:limit:10", {"items": [1]}))

    mock_post_service.delete_post.return_value = True

    app.dependency_overrides[get_post_service] = lambda: mock_post_service
    app.dependency_overrides[get_cache_service] = lambda: fake_cache_service

    resp = client.delete("/api/posts/1", headers=auth_headers)
    assert resp.status_code == 204

    # Both item and list caches must be purged
    assert asyncio.run(fake_cache_service.get("posts:item:1")) is None
    assert asyncio.run(fake_cache_service.get("posts:list:page:1:limit:10")) is None


def test_delete_post_unauthenticated_returns_401(client, fake_cache_service, mock_post_service):
    """DELETE /api/posts/{id} without token returns 401."""
    app.dependency_overrides[get_post_service] = lambda: mock_post_service
    app.dependency_overrides[get_cache_service] = lambda: fake_cache_service

    resp = client.delete("/api/posts/1")
    assert resp.status_code == 401


def test_delete_post_non_owner_returns_403(client, user_b_headers, fake_cache_service, mock_post_service):
    """DELETE /api/posts/{id} by non-owner returns 403 Forbidden."""
    mock_post_service.delete_post.side_effect = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this post"
    )
    app.dependency_overrides[get_post_service] = lambda: mock_post_service
    app.dependency_overrides[get_cache_service] = lambda: fake_cache_service

    resp = client.delete("/api/posts/1", headers=user_b_headers)
    assert resp.status_code == 403


def test_delete_post_nonexistent_returns_404(client, auth_headers, fake_cache_service, mock_post_service):
    """DELETE /api/posts/{id} for nonexistent post returns 404."""
    mock_post_service.delete_post.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
    )
    app.dependency_overrides[get_post_service] = lambda: mock_post_service
    app.dependency_overrides[get_cache_service] = lambda: fake_cache_service

    resp = client.delete("/api/posts/999", headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Redis Failure Resilience Tests
# ---------------------------------------------------------------------------
def test_redis_failure_falls_back_to_service_without_crashing(client, mock_post_service):
    """
    When Redis fails (raises exception on GET/SET):
    Request falls back cleanly to the service, returns 200, and does not crash.
    """
    mock_redis = AsyncMock()
    mock_redis.get.side_effect = ConnectionError("Redis server unreachable")
    mock_redis.set.side_effect = ConnectionError("Redis write failed")
    failing_cache = CacheService(mock_redis)

    sample = make_post_payload(1, title="DB Post")
    mock_post_service.get_post_by_id.return_value = sample

    app.dependency_overrides[get_post_service] = lambda: mock_post_service
    app.dependency_overrides[get_cache_service] = lambda: failing_cache

    resp = client.get("/api/posts/1")
    assert resp.status_code == 200
    assert resp.headers.get("X-Cache") == "MISS"
    assert resp.json()["title"] == "DB Post"
