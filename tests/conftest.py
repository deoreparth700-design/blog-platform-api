"""
Global Pytest Configuration and Test Fixtures for Blog Platform API.

This module provides:
1. JWT test isolation using dedicated TEST_JWT_SECRET without mutating shell environment
2. User identities (User A, User B)
3. Dynamic JWT tokens (valid User A, valid User B, expired, invalid)
4. Authorization header fixtures
5. FastAPI TestClient with automatic dependency overrides cleanup
6. In-memory FakeRedis client matching Upstash async Redis API
7. CacheService fixture wrapping FakeRedis
8. Lightweight Mock and Fake Services for route/API testing
9. Reusable sample data fixtures
"""

import time
import fnmatch
from typing import Dict, Tuple, Optional, List, Any
from datetime import datetime, timezone
from uuid import UUID
from unittest.mock import AsyncMock

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, message=r".*BlockingPortal.*")

import pytest
import jwt
from fastapi.testclient import TestClient

from src.app import app
from src.services.cache_service import CacheService
from src.services.post_service import PostService
from src.services.comment_service import CommentService
from src.services.like_service import LikeService
from src.routes.posts import get_post_service, get_cache_service
from src.routes.comments import get_comment_service
from src.routes.likes import get_like_service


# ---------------------------------------------------------------------------
# Test Constants & JWT Isolation
# ---------------------------------------------------------------------------
TEST_JWT_SECRET = "test-only-blog-platform-jwt-secret"

USER_A_ID = "11111111-1111-1111-1111-111111111111"
USER_B_ID = "22222222-2222-2222-2222-222222222222"


@pytest.fixture(autouse=True)
def isolate_jwt_secret(monkeypatch):
    """
    Ensure automated tests never use the real JWT_ACCESS_SECRET.
    Monkeypatches JWT_ACCESS_SECRET for test execution without mutating
    the permanent shell environment.
    """
    monkeypatch.setenv("JWT_ACCESS_SECRET", TEST_JWT_SECRET)


# ---------------------------------------------------------------------------
# Identity & Dynamic JWT Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def user_a_id() -> str:
    return USER_A_ID


@pytest.fixture
def user_b_id() -> str:
    return USER_B_ID


@pytest.fixture
def user_a_identity(user_a_id) -> dict:
    return {"userId": user_a_id}


@pytest.fixture
def user_b_identity(user_b_id) -> dict:
    return {"userId": user_b_id}


@pytest.fixture
def user_a_token(user_a_id) -> str:
    payload = {
        "userId": user_a_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


@pytest.fixture
def user_b_token(user_b_id) -> str:
    payload = {
        "userId": user_b_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


@pytest.fixture
def expired_token(user_a_id) -> str:
    payload = {
        "userId": user_a_id,
        "iat": int(time.time()) - 7200,
        "exp": int(time.time()) - 3600,
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


@pytest.fixture
def invalid_token() -> str:
    return "invalid.jwt.token.structure"


@pytest.fixture
def auth_headers(user_a_token) -> dict:
    return {"Authorization": f"Bearer {user_a_token}"}


@pytest.fixture
def user_b_headers(user_b_token) -> dict:
    return {"Authorization": f"Bearer {user_b_token}"}


@pytest.fixture
def expired_headers(expired_token) -> dict:
    return {"Authorization": f"Bearer {expired_token}"}


@pytest.fixture
def invalid_headers(invalid_token) -> dict:
    return {"Authorization": f"Bearer {invalid_token}"}


# ---------------------------------------------------------------------------
# FastAPI TestClient Fixture with Guaranteed Cleanup
# ---------------------------------------------------------------------------
@pytest.fixture
def client():
    """
    FastAPI TestClient fixture with guaranteed teardown of dependency overrides.
    """
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# In-Memory Fake Redis
# ---------------------------------------------------------------------------
class FakeRedis:
    """
    In-memory async Redis client matching the operations used by CacheService:
    - get(key)
    - set(key, value, ex=None)
    - delete(*keys)
    - keys(pattern)
    - ttl(key)
    - flushdb()
    """

    def __init__(self):
        # key -> (value_str, expire_at_timestamp)
        self._store: Dict[str, Tuple[str, Optional[float]]] = {}

    def _is_expired(self, key: str) -> bool:
        if key not in self._store:
            return True
        _, expire_at = self._store[key]
        if expire_at is not None and time.time() >= expire_at:
            del self._store[key]
            return True
        return False

    async def get(self, key: str) -> Optional[str]:
        if self._is_expired(key):
            return None
        val, _ = self._store[key]
        return val

    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        expire_at = (time.time() + ex) if ex is not None else None
        self._store[key] = (str(value), expire_at)
        return True

    async def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                count += 1
        return count

    async def keys(self, pattern: str = "*") -> List[str]:
        active_keys = [k for k in list(self._store.keys()) if not self._is_expired(k)]
        return fnmatch.filter(active_keys, pattern)

    async def ttl(self, key: str) -> int:
        if self._is_expired(key):
            return -2
        _, expire_at = self._store[key]
        if expire_at is None:
            return -1
        remaining = int(expire_at - time.time())
        return max(0, remaining)

    async def flushdb(self) -> bool:
        self._store.clear()
        return True


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
def fake_cache_service(fake_redis) -> CacheService:
    return CacheService(fake_redis)


# ---------------------------------------------------------------------------
# Lightweight Test Doubles for API Route Testing
# (Do NOT duplicate business logic of real services)
# ---------------------------------------------------------------------------
class FakePostService:
    """
    Lightweight test double for route testing.
    Does NOT duplicate ownership, existence, or pagination business logic.
    """

    def __init__(self):
        self.posts: Dict[int, dict] = {}
        self.next_id = 1

    async def create_post(self, author_id: str, post_data) -> dict:
        post = {
            "id": self.next_id,
            "author_id": UUID(author_id) if isinstance(author_id, str) else author_id,
            "title": post_data.title,
            "content": post_data.content,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        self.posts[self.next_id] = post
        self.next_id += 1
        return post

    async def get_posts(self, page: int = 1, limit: int = 10) -> dict:
        items = list(self.posts.values())
        return {
            "items": items,
            "page": page,
            "limit": limit,
            "total": len(items),
            "total_pages": 1 if items else 0,
        }

    async def get_post_by_id(self, post_id: int) -> dict:
        return self.posts.get(post_id, {
            "id": post_id,
            "author_id": UUID(USER_A_ID),
            "title": f"Post {post_id}",
            "content": "Content",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        })

    async def update_post(self, post_id: int, user_id: str, post_data) -> dict:
        return {
            "id": post_id,
            "author_id": UUID(user_id) if isinstance(user_id, str) else user_id,
            "title": post_data.title or "Updated",
            "content": post_data.content or "Updated Content",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

    async def delete_post(self, post_id: int, user_id: str) -> bool:
        if post_id in self.posts:
            del self.posts[post_id]
        return True


@pytest.fixture
def fake_post_service() -> FakePostService:
    return FakePostService()


@pytest.fixture
def mock_post_service() -> AsyncMock:
    """AsyncMock test double for PostService."""
    return AsyncMock(spec=PostService)


@pytest.fixture
def mock_comment_service() -> AsyncMock:
    """AsyncMock test double for CommentService."""
    return AsyncMock(spec=CommentService)


@pytest.fixture
def mock_like_service() -> AsyncMock:
    """AsyncMock test double for LikeService."""
    return AsyncMock(spec=LikeService)


# ---------------------------------------------------------------------------
# Sample Data Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_post_data(user_a_id) -> dict:
    return {
        "id": 1,
        "author_id": UUID(user_a_id),
        "title": "Sample Post Title",
        "content": "Sample Post Content body for testing.",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


@pytest.fixture
def sample_comment_data(user_a_id) -> dict:
    return {
        "id": 1,
        "post_id": 1,
        "author_id": UUID(user_a_id),
        "content": "Sample Comment Content.",
        "created_at": datetime.now(timezone.utc),
    }


@pytest.fixture
def sample_like_data() -> dict:
    return {
        "post_id": 1,
        "like_count": 3,
    }
