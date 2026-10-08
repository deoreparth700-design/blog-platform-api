"""
Infrastructure smoke test to validate that:
1. TestClient(app) works with root endpoints
2. JWT fixtures (valid, expired, invalid) work with auth middleware
3. Dependency overrides cleanly mock services without database/Redis
4. FakeRedis handles get, set with TTL, and wildcard key deletion
"""

import pytest
from src.app import app
from src.routes.posts import get_post_service, get_cache_service
from src.schemas.post import PostCreate


def test_testclient_and_health(client):
    """TestClient reaches FastAPI application."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_jwt_fixtures_and_auth(client, auth_headers, expired_headers, invalid_headers):
    """JWT fixtures validate correctly against existing auth middleware."""
    # Valid User A token
    resp_valid = client.get("/api/auth-test", headers=auth_headers)
    assert resp_valid.status_code == 200
    assert resp_valid.json()["authenticated"] is True

    # Expired token -> 401
    resp_expired = client.get("/api/auth-test", headers=expired_headers)
    assert resp_expired.status_code == 401

    # Invalid token -> 401
    resp_invalid = client.get("/api/auth-test", headers=invalid_headers)
    assert resp_invalid.status_code == 401


def test_dependency_overrides(client, auth_headers, fake_post_service, fake_cache_service):
    """FastAPI dependency overrides replace real DB/Redis services seamlessly."""
    app.dependency_overrides[get_post_service] = lambda: fake_post_service
    app.dependency_overrides[get_cache_service] = lambda: fake_cache_service

    # Create post via fake service
    create_resp = client.post("/api/posts/", json={"title": "Smoke Title", "content": "Smoke Content"}, headers=auth_headers)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["title"] == "Smoke Title"

    # List posts via fake service
    list_resp = client.get("/api/posts/", params={"page": 1, "limit": 5})
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Smoke Title"


@pytest.mark.asyncio
async def test_fake_redis_operations(fake_redis):
    """FakeRedis supports get, set with TTL, keys pattern matching, and deletion."""
    await fake_redis.set("posts:item:1", '{"title": "Test"}', ex=300)
    await fake_redis.set("posts:list:page:1", '{"items": []}', ex=60)

    # get
    val = await fake_redis.get("posts:item:1")
    assert val == '{"title": "Test"}'

    # ttl
    ttl_val = await fake_redis.ttl("posts:item:1")
    assert 0 < ttl_val <= 300

    # pattern matching & deletion
    matching = await fake_redis.keys("posts:list:*")
    assert "posts:list:page:1" in matching
    deleted = await fake_redis.delete(*matching)
    assert deleted == 1

    remaining = await fake_redis.keys("posts:list:*")
    assert len(remaining) == 0
