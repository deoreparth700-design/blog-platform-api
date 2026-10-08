"""
Unit Tests for CommentService (src/services/comment_service.py).

Tests the REAL CommentService class with mocked repositories:
- create comment on existing post
- create comment on missing post (404)
- create comment with invalid user UUID (400)
- fetch comments for existing post
- fetch comments for missing parent post (404)
- update comment by owner (success)
- update comment by non-owner (403)
- update missing comment (404)
- update comment with invalid user UUID (400)
- delete comment by owner (success)
- delete comment by non-owner (403)
- delete missing comment (404)
- delete comment with invalid user UUID (400)
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID
from datetime import datetime, timezone
import pytest
from fastapi import HTTPException

from src.services.comment_service import CommentService
from src.schemas.comment import CommentCreate, CommentUpdate
from tests.conftest import USER_A_ID, USER_B_ID


@pytest.fixture
def comment_service_with_mock_repos():
    """Instantiate a real CommentService with mocked comment and post repositories."""
    dummy_pool = MagicMock()
    service = CommentService(dummy_pool)
    service.repository = AsyncMock()
    service.post_repository = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_create_comment_on_existing_post(comment_service_with_mock_repos):
    """create_comment successfully creates comment when parent post exists."""
    comment_service_with_mock_repos.post_repository.get_post_by_id.return_value = {"id": 1}
    created_comment = {
        "id": 10,
        "post_id": 1,
        "author_id": UUID(USER_A_ID),
        "content": "Nice post!",
        "created_at": datetime.now(timezone.utc),
    }
    comment_service_with_mock_repos.repository.create_comment.return_value = created_comment

    payload = CommentCreate(content="Nice post!")
    result = await comment_service_with_mock_repos.create_comment(1, USER_A_ID, payload)

    assert result["id"] == 10
    assert result["content"] == "Nice post!"
    comment_service_with_mock_repos.repository.create_comment.assert_awaited_once_with(
        1, UUID(USER_A_ID), "Nice post!"
    )


@pytest.mark.asyncio
async def test_create_comment_on_missing_post(comment_service_with_mock_repos):
    """create_comment raises 404 when parent post does not exist."""
    comment_service_with_mock_repos.post_repository.get_post_by_id.return_value = None

    with pytest.raises(HTTPException) as exc:
        await comment_service_with_mock_repos.create_comment(999, USER_A_ID, CommentCreate(content="Hello"))

    assert exc.value.status_code == 404
    assert exc.value.detail == "Post not found"


@pytest.mark.asyncio
async def test_create_comment_invalid_user_uuid(comment_service_with_mock_repos):
    """create_comment raises 400 when user_id is not a valid UUID."""
    comment_service_with_mock_repos.post_repository.get_post_by_id.return_value = {"id": 1}

    with pytest.raises(HTTPException) as exc:
        await comment_service_with_mock_repos.create_comment(1, "bad-uuid", CommentCreate(content="Hello"))

    assert exc.value.status_code == 400
    assert "Invalid user ID format" in exc.value.detail


@pytest.mark.asyncio
async def test_get_comments_by_post_id_existing(comment_service_with_mock_repos):
    """get_comments_by_post_id returns comments when post exists."""
    comment_service_with_mock_repos.post_repository.get_post_by_id.return_value = {"id": 1}
    expected_comments = [{"id": 1, "content": "First"}, {"id": 2, "content": "Second"}]
    comment_service_with_mock_repos.repository.get_comments_by_post_id.return_value = expected_comments

    res = await comment_service_with_mock_repos.get_comments_by_post_id(1)
    assert res == expected_comments


@pytest.mark.asyncio
async def test_get_comments_by_post_id_missing_post(comment_service_with_mock_repos):
    """get_comments_by_post_id raises 404 when parent post does not exist."""
    comment_service_with_mock_repos.post_repository.get_post_by_id.return_value = None

    with pytest.raises(HTTPException) as exc:
        await comment_service_with_mock_repos.get_comments_by_post_id(999)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Post not found"


@pytest.mark.asyncio
async def test_update_comment_by_owner(comment_service_with_mock_repos):
    """Comment owner can update comment."""
    existing = {"id": 5, "author_id": UUID(USER_A_ID), "content": "Original"}
    updated = {"id": 5, "author_id": UUID(USER_A_ID), "content": "Edited"}
    comment_service_with_mock_repos.repository.get_comment_by_id.return_value = existing
    comment_service_with_mock_repos.repository.update_comment.return_value = updated

    res = await comment_service_with_mock_repos.update_comment(5, USER_A_ID, CommentUpdate(content="Edited"))
    assert res["content"] == "Edited"
    comment_service_with_mock_repos.repository.update_comment.assert_awaited_once_with(5, "Edited")


@pytest.mark.asyncio
async def test_update_comment_by_non_owner(comment_service_with_mock_repos):
    """Non-owner receives 403 Forbidden when attempting to update comment."""
    existing = {"id": 5, "author_id": UUID(USER_A_ID), "content": "Original"}
    comment_service_with_mock_repos.repository.get_comment_by_id.return_value = existing

    with pytest.raises(HTTPException) as exc:
        await comment_service_with_mock_repos.update_comment(5, USER_B_ID, CommentUpdate(content="Hacked"))

    assert exc.value.status_code == 403
    assert "Not authorized" in exc.value.detail


@pytest.mark.asyncio
async def test_update_comment_missing(comment_service_with_mock_repos):
    """Updating a non-existent comment raises 404."""
    comment_service_with_mock_repos.repository.get_comment_by_id.return_value = None

    with pytest.raises(HTTPException) as exc:
        await comment_service_with_mock_repos.update_comment(999, USER_A_ID, CommentUpdate(content="Test"))

    assert exc.value.status_code == 404
    assert exc.value.detail == "Comment not found"


@pytest.mark.asyncio
async def test_update_comment_invalid_user_uuid(comment_service_with_mock_repos):
    """Updating a comment with invalid user UUID raises 400."""
    existing = {"id": 5, "author_id": UUID(USER_A_ID), "content": "Original"}
    comment_service_with_mock_repos.repository.get_comment_by_id.return_value = existing

    with pytest.raises(HTTPException) as exc:
        await comment_service_with_mock_repos.update_comment(5, "invalid-uuid", CommentUpdate(content="Test"))

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_delete_comment_by_owner(comment_service_with_mock_repos):
    """Comment owner can delete comment."""
    existing = {"id": 5, "author_id": UUID(USER_A_ID)}
    comment_service_with_mock_repos.repository.get_comment_by_id.return_value = existing
    comment_service_with_mock_repos.repository.delete_comment.return_value = True

    res = await comment_service_with_mock_repos.delete_comment(5, USER_A_ID)
    assert res is True
    comment_service_with_mock_repos.repository.delete_comment.assert_awaited_once_with(5)


@pytest.mark.asyncio
async def test_delete_comment_by_non_owner(comment_service_with_mock_repos):
    """Non-owner receives 403 Forbidden when attempting to delete comment."""
    existing = {"id": 5, "author_id": UUID(USER_A_ID)}
    comment_service_with_mock_repos.repository.get_comment_by_id.return_value = existing

    with pytest.raises(HTTPException) as exc:
        await comment_service_with_mock_repos.delete_comment(5, USER_B_ID)

    assert exc.value.status_code == 403
    assert "Not authorized" in exc.value.detail


@pytest.mark.asyncio
async def test_delete_comment_missing(comment_service_with_mock_repos):
    """Deleting a non-existent comment raises 404."""
    comment_service_with_mock_repos.repository.get_comment_by_id.return_value = None

    with pytest.raises(HTTPException) as exc:
        await comment_service_with_mock_repos.delete_comment(999, USER_A_ID)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Comment not found"


@pytest.mark.asyncio
async def test_delete_comment_invalid_user_uuid(comment_service_with_mock_repos):
    """Deleting a comment with invalid user UUID raises 400."""
    existing = {"id": 5, "author_id": UUID(USER_A_ID)}
    comment_service_with_mock_repos.repository.get_comment_by_id.return_value = existing

    with pytest.raises(HTTPException) as exc:
        await comment_service_with_mock_repos.delete_comment(5, "not-a-valid-uuid")

    assert exc.value.status_code == 400
