"""
Unit Tests for LikeService (src/services/like_service.py).

Tests the REAL LikeService class with mocked repositories:
- like existing post
- like missing post (404)
- like with invalid user UUID (400)
- duplicate like (409)
- unlike existing like
- unlike missing post (404)
- unlike absent like (404)
- unlike with invalid user UUID (400)
- get like count for existing post
- get like count for missing post (404)
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID
import pytest
from fastapi import HTTPException

from src.services.like_service import LikeService
from tests.conftest import USER_A_ID


@pytest.fixture
def like_service_with_mock_repos():
    """Instantiate a real LikeService with mocked like and post repositories."""
    dummy_pool = MagicMock()
    service = LikeService(dummy_pool)
    service.repository = AsyncMock()
    service.post_repository = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_like_existing_post(like_service_with_mock_repos):
    """like_post creates like when post exists and user has not liked it yet."""
    like_service_with_mock_repos.post_repository.get_post_by_id.return_value = {"id": 1}
    like_service_with_mock_repos.repository.like_exists.return_value = False

    result = await like_service_with_mock_repos.like_post(1, USER_A_ID)

    assert result["message"] == "Post liked"
    assert result["post_id"] == 1
    like_service_with_mock_repos.repository.create_like.assert_awaited_once_with(1, UUID(USER_A_ID))


@pytest.mark.asyncio
async def test_like_missing_post(like_service_with_mock_repos):
    """like_post raises 404 when target post does not exist."""
    like_service_with_mock_repos.post_repository.get_post_by_id.return_value = None

    with pytest.raises(HTTPException) as exc:
        await like_service_with_mock_repos.like_post(999, USER_A_ID)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Post not found"


@pytest.mark.asyncio
async def test_like_invalid_user_uuid(like_service_with_mock_repos):
    """like_post raises 400 when user ID is not a valid UUID."""
    with pytest.raises(HTTPException) as exc:
        await like_service_with_mock_repos.like_post(1, "invalid-uuid")

    assert exc.value.status_code == 400
    assert "Invalid user ID format" in exc.value.detail


@pytest.mark.asyncio
async def test_duplicate_like_conflict(like_service_with_mock_repos):
    """like_post raises 409 Conflict when user has already liked the post."""
    like_service_with_mock_repos.post_repository.get_post_by_id.return_value = {"id": 1}
    like_service_with_mock_repos.repository.like_exists.return_value = True

    with pytest.raises(HTTPException) as exc:
        await like_service_with_mock_repos.like_post(1, USER_A_ID)

    assert exc.value.status_code == 409
    assert exc.value.detail == "Post already liked"


@pytest.mark.asyncio
async def test_unlike_existing_like(like_service_with_mock_repos):
    """unlike_post deletes like when post and like exist."""
    like_service_with_mock_repos.post_repository.get_post_by_id.return_value = {"id": 1}
    like_service_with_mock_repos.repository.like_exists.return_value = True

    await like_service_with_mock_repos.unlike_post(1, USER_A_ID)

    like_service_with_mock_repos.repository.delete_like.assert_awaited_once_with(1, UUID(USER_A_ID))


@pytest.mark.asyncio
async def test_unlike_missing_post(like_service_with_mock_repos):
    """unlike_post raises 404 when parent post does not exist."""
    like_service_with_mock_repos.post_repository.get_post_by_id.return_value = None

    with pytest.raises(HTTPException) as exc:
        await like_service_with_mock_repos.unlike_post(999, USER_A_ID)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Post not found"


@pytest.mark.asyncio
async def test_unlike_absent_like(like_service_with_mock_repos):
    """unlike_post raises 404 when user has not previously liked the post."""
    like_service_with_mock_repos.post_repository.get_post_by_id.return_value = {"id": 1}
    like_service_with_mock_repos.repository.like_exists.return_value = False

    with pytest.raises(HTTPException) as exc:
        await like_service_with_mock_repos.unlike_post(1, USER_A_ID)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Like not found"


@pytest.mark.asyncio
async def test_unlike_invalid_user_uuid(like_service_with_mock_repos):
    """unlike_post raises 400 when user ID is invalid UUID."""
    with pytest.raises(HTTPException) as exc:
        await like_service_with_mock_repos.unlike_post(1, "bad-uuid")

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_get_like_count_existing_post(like_service_with_mock_repos):
    """get_like_count returns count when post exists."""
    like_service_with_mock_repos.post_repository.get_post_by_id.return_value = {"id": 1}
    like_service_with_mock_repos.repository.get_like_count.return_value = 7

    res = await like_service_with_mock_repos.get_like_count(1)
    assert res == {"post_id": 1, "like_count": 7}


@pytest.mark.asyncio
async def test_get_like_count_missing_post(like_service_with_mock_repos):
    """get_like_count raises 404 when post does not exist."""
    like_service_with_mock_repos.post_repository.get_post_by_id.return_value = None

    with pytest.raises(HTTPException) as exc:
        await like_service_with_mock_repos.get_like_count(999)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Post not found"
