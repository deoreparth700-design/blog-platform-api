"""
Unit Tests for PostService (src/services/post_service.py).

Tests the REAL PostService class with a mocked PostRepository:
- create with valid UUID
- create with invalid author UUID (400)
- get paginated posts and total_pages calculation
- get existing post
- get missing post (404)
- update by owner (success)
- update by non-owner (403)
- update with invalid user UUID (400)
- update when repository returns None (404)
- delete by owner (success)
- delete by non-owner (403)
- delete with invalid user UUID (400)
- delete when repository returns False (404)
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID
from datetime import datetime, timezone
import pytest
from fastapi import HTTPException

from src.services.post_service import PostService
from src.schemas.post import PostCreate, PostUpdate
from tests.conftest import USER_A_ID, USER_B_ID


@pytest.fixture
def post_service_with_mock_repo():
    """Instantiate a real PostService with a mocked repository."""
    dummy_pool = MagicMock()
    service = PostService(dummy_pool)
    service.repository = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_create_post_valid_uuid(post_service_with_mock_repo):
    """create_post parses valid UUID and calls repository.create_post."""
    post_data = PostCreate(title="Test Title", content="Test Content")
    expected_row = {
        "id": 1,
        "author_id": UUID(USER_A_ID),
        "title": "Test Title",
        "content": "Test Content",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    post_service_with_mock_repo.repository.create_post.return_value = expected_row

    result = await post_service_with_mock_repo.create_post(USER_A_ID, post_data)
    assert result["id"] == 1
    assert result["title"] == "Test Title"
    post_service_with_mock_repo.repository.create_post.assert_awaited_once_with(
        UUID(USER_A_ID), "Test Title", "Test Content"
    )


@pytest.mark.asyncio
async def test_create_post_invalid_uuid(post_service_with_mock_repo):
    """create_post raises 400 when author_id is not a valid UUID."""
    post_data = PostCreate(title="Test", content="Test")
    with pytest.raises(HTTPException) as exc:
        await post_service_with_mock_repo.create_post("invalid-uuid-string", post_data)

    assert exc.value.status_code == 400
    assert "Invalid author ID format" in exc.value.detail


@pytest.mark.asyncio
async def test_get_posts_pagination_and_total_pages(post_service_with_mock_repo):
    """get_posts correctly calculates total_pages across various limits."""
    # Case 1: 25 items with limit 10 -> 3 pages
    post_service_with_mock_repo.repository.get_posts.return_value = ([{"id": 1}], 25)
    res = await post_service_with_mock_repo.get_posts(page=1, limit=10)
    assert res["total"] == 25
    assert res["total_pages"] == 3
    assert res["page"] == 1
    assert res["limit"] == 10

    # Case 2: 0 items -> 0 pages
    post_service_with_mock_repo.repository.get_posts.return_value = ([], 0)
    res_zero = await post_service_with_mock_repo.get_posts(page=1, limit=10)
    assert res_zero["total"] == 0
    assert res_zero["total_pages"] == 0


@pytest.mark.asyncio
async def test_get_post_by_id_existing(post_service_with_mock_repo):
    """get_post_by_id returns post if found."""
    expected = {"id": 1, "title": "Found"}
    post_service_with_mock_repo.repository.get_post_by_id.return_value = expected

    result = await post_service_with_mock_repo.get_post_by_id(1)
    assert result == expected


@pytest.mark.asyncio
async def test_get_post_by_id_missing_404(post_service_with_mock_repo):
    """get_post_by_id raises 404 if post does not exist."""
    post_service_with_mock_repo.repository.get_post_by_id.return_value = None

    with pytest.raises(HTTPException) as exc:
        await post_service_with_mock_repo.get_post_by_id(999)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Post not found"


@pytest.mark.asyncio
async def test_update_post_by_owner(post_service_with_mock_repo):
    """Owner can update their post."""
    existing_post = {
        "id": 1,
        "author_id": UUID(USER_A_ID),
        "title": "Old Title",
        "content": "Old Content",
    }
    updated_post = {
        "id": 1,
        "author_id": UUID(USER_A_ID),
        "title": "New Title",
        "content": "New Content",
    }
    post_service_with_mock_repo.repository.get_post_by_id.return_value = existing_post
    post_service_with_mock_repo.repository.update_post.return_value = updated_post

    update_data = PostUpdate(title="New Title", content="New Content")
    result = await post_service_with_mock_repo.update_post(1, USER_A_ID, update_data)

    assert result["title"] == "New Title"
    post_service_with_mock_repo.repository.update_post.assert_awaited_once_with(
        1, "New Title", "New Content"
    )


@pytest.mark.asyncio
async def test_update_post_by_non_owner_forbidden(post_service_with_mock_repo):
    """Non-owner attempting to update post receives 403 Forbidden."""
    existing_post = {
        "id": 1,
        "author_id": UUID(USER_A_ID),
        "title": "User A Post",
        "content": "Content",
    }
    post_service_with_mock_repo.repository.get_post_by_id.return_value = existing_post

    update_data = PostUpdate(title="Hacked")
    with pytest.raises(HTTPException) as exc:
        await post_service_with_mock_repo.update_post(1, USER_B_ID, update_data)

    assert exc.value.status_code == 403
    assert "Not authorized" in exc.value.detail


@pytest.mark.asyncio
async def test_update_post_invalid_user_uuid(post_service_with_mock_repo):
    """Invalid user UUID raises 400 Bad Request."""
    existing_post = {"id": 1, "author_id": UUID(USER_A_ID)}
    post_service_with_mock_repo.repository.get_post_by_id.return_value = existing_post

    with pytest.raises(HTTPException) as exc:
        await post_service_with_mock_repo.update_post(1, "bad-uuid", PostUpdate(title="X"))

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_post_repository_missing_resource(post_service_with_mock_repo):
    """If repository update returns None (concurrency deletion), raises 404."""
    existing_post = {"id": 1, "author_id": UUID(USER_A_ID)}
    post_service_with_mock_repo.repository.get_post_by_id.return_value = existing_post
    post_service_with_mock_repo.repository.update_post.return_value = None

    with pytest.raises(HTTPException) as exc:
        await post_service_with_mock_repo.update_post(1, USER_A_ID, PostUpdate(title="X"))

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_post_by_owner(post_service_with_mock_repo):
    """Owner can delete their post."""
    existing_post = {"id": 1, "author_id": UUID(USER_A_ID)}
    post_service_with_mock_repo.repository.get_post_by_id.return_value = existing_post
    post_service_with_mock_repo.repository.delete_post.return_value = True

    result = await post_service_with_mock_repo.delete_post(1, USER_A_ID)
    assert result is True
    post_service_with_mock_repo.repository.delete_post.assert_awaited_once_with(1)


@pytest.mark.asyncio
async def test_delete_post_by_non_owner_forbidden(post_service_with_mock_repo):
    """Non-owner attempting to delete post receives 403 Forbidden."""
    existing_post = {"id": 1, "author_id": UUID(USER_A_ID)}
    post_service_with_mock_repo.repository.get_post_by_id.return_value = existing_post

    with pytest.raises(HTTPException) as exc:
        await post_service_with_mock_repo.delete_post(1, USER_B_ID)

    assert exc.value.status_code == 403
    assert "Not authorized" in exc.value.detail


@pytest.mark.asyncio
async def test_delete_post_invalid_user_uuid(post_service_with_mock_repo):
    """delete_post with invalid user UUID raises 400."""
    existing_post = {"id": 1, "author_id": UUID(USER_A_ID)}
    post_service_with_mock_repo.repository.get_post_by_id.return_value = existing_post

    with pytest.raises(HTTPException) as exc:
        await post_service_with_mock_repo.delete_post(1, "bad-uuid")

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_delete_post_repository_returns_false(post_service_with_mock_repo):
    """If repository delete returns False, raises 404."""
    existing_post = {"id": 1, "author_id": UUID(USER_A_ID)}
    post_service_with_mock_repo.repository.get_post_by_id.return_value = existing_post
    post_service_with_mock_repo.repository.delete_post.return_value = False

    with pytest.raises(HTTPException) as exc:
        await post_service_with_mock_repo.delete_post(1, USER_A_ID)

    assert exc.value.status_code == 404
