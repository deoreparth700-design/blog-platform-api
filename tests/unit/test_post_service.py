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


@pytest.mark.asyncio
async def test_get_post_detail_existing(post_service_with_mock_repo):
    """get_post_detail calls repository.get_post_with_comments."""
    expected = {"id": 1, "title": "Detail", "comments": [{"id": 10, "content": "Hi"}]}
    post_service_with_mock_repo.repository.get_post_with_comments.return_value = expected

    result = await post_service_with_mock_repo.get_post_detail(1)
    assert result == expected
    post_service_with_mock_repo.repository.get_post_with_comments.assert_awaited_once_with(1)
    post_service_with_mock_repo.repository.get_post_by_id.assert_not_called()


@pytest.mark.asyncio
async def test_get_post_detail_missing_404(post_service_with_mock_repo):
    """get_post_detail raises 404 when get_post_with_comments returns None."""
    post_service_with_mock_repo.repository.get_post_with_comments.return_value = None

    with pytest.raises(HTTPException) as exc:
        await post_service_with_mock_repo.get_post_detail(999)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Post not found"


@pytest.mark.asyncio
async def test_post_service_update_and_delete_do_not_call_get_post_with_comments(post_service_with_mock_repo):
    """PostService update_post and delete_post use lightweight get_post_by_id, NOT get_post_with_comments."""
    post_service_with_mock_repo.repository.get_post_by_id.return_value = {
        "id": 1,
        "author_id": UUID(USER_A_ID),
        "title": "Old",
        "content": "Old",
    }
    post_service_with_mock_repo.repository.update_post.return_value = {
        "id": 1,
        "author_id": UUID(USER_A_ID),
        "title": "New",
        "content": "New",
    }
    post_service_with_mock_repo.repository.delete_post.return_value = True

    # Test update
    await post_service_with_mock_repo.update_post(1, USER_A_ID, PostUpdate(title="New"))
    post_service_with_mock_repo.repository.get_post_with_comments.assert_not_called()
    assert post_service_with_mock_repo.repository.get_post_by_id.await_count == 1

    # Test delete
    await post_service_with_mock_repo.delete_post(1, USER_A_ID)
    post_service_with_mock_repo.repository.get_post_with_comments.assert_not_called()
    assert post_service_with_mock_repo.repository.get_post_by_id.await_count == 2


def test_encode_decode_cursor_roundtrip():
    """encode_cursor and decode_cursor successfully round-trip created_at and id."""
    from src.services.post_service import encode_cursor, decode_cursor
    now = datetime(2026, 10, 11, 12, 0, 0, tzinfo=timezone.utc)
    post_id = 42

    cursor = encode_cursor(now, post_id)
    assert isinstance(cursor, str)

    decoded_dt, decoded_id = decode_cursor(cursor)
    assert decoded_dt == now
    assert decoded_id == post_id


def test_decode_cursor_invalid_formats_raise_400():
    """decode_cursor raises 400 Bad Request on malformed base64, missing parts, or invalid types."""
    from src.services.post_service import decode_cursor
    import base64

    # 1. Non-base64 garbage
    with pytest.raises(HTTPException) as exc1:
        decode_cursor("!!!invalid-base64!!!")
    assert exc1.value.status_code == 400
    assert "Invalid cursor format" in exc1.value.detail

    # 2. Base64 but no pipe separator
    no_pipe = base64.urlsafe_b64encode(b"nopipeshere").decode()
    with pytest.raises(HTTPException) as exc2:
        decode_cursor(no_pipe)
    assert exc2.value.status_code == 400
    assert "Invalid cursor format" in exc2.value.detail

    # 3. Base64 with invalid datetime
    bad_date = base64.urlsafe_b64encode(b"not-a-date|42").decode()
    with pytest.raises(HTTPException) as exc3:
        decode_cursor(bad_date)
    assert exc3.value.status_code == 400
    assert "Invalid cursor format" in exc3.value.detail

    # 4. Base64 with invalid ID
    bad_id = base64.urlsafe_b64encode(b"2026-10-11T12:00:00+00:00|not-an-id").decode()
    with pytest.raises(HTTPException) as exc4:
        decode_cursor(bad_id)
    assert exc4.value.status_code == 400
    assert "Invalid cursor format" in exc4.value.detail


@pytest.mark.asyncio
async def test_get_posts_feed_first_page_generates_next_cursor(post_service_with_mock_repo):
    """get_posts_feed returns items, has_more=True, and valid next_cursor on page 1."""
    now = datetime(2026, 10, 11, 12, 0, 0, tzinfo=timezone.utc)
    mock_items = [
        {"id": 2, "title": "Second", "created_at": now},
        {"id": 1, "title": "First", "created_at": now},
    ]
    post_service_with_mock_repo.repository.get_posts_feed.return_value = (mock_items, True)

    result = await post_service_with_mock_repo.get_posts_feed(limit=2, cursor=None)

    assert result["has_more"] is True
    assert len(result["items"]) == 2
    assert result["next_cursor"] is not None

    # Decode next_cursor to ensure it matches the last item (id=1)
    from src.services.post_service import decode_cursor
    cur_dt, cur_id = decode_cursor(result["next_cursor"])
    assert cur_dt == now
    assert cur_id == 1


@pytest.mark.asyncio
async def test_get_posts_feed_last_page_no_next_cursor(post_service_with_mock_repo):
    """get_posts_feed returns has_more=False and next_cursor=None on the final page."""
    now = datetime(2026, 10, 11, 12, 0, 0, tzinfo=timezone.utc)
    mock_items = [
        {"id": 1, "title": "Last Post", "created_at": now},
    ]
    post_service_with_mock_repo.repository.get_posts_feed.return_value = (mock_items, False)

    from src.services.post_service import encode_cursor
    prev_cursor = encode_cursor(now, 5)
    result = await post_service_with_mock_repo.get_posts_feed(limit=2, cursor=prev_cursor)

    assert result["has_more"] is False
    assert len(result["items"]) == 1
    assert result["next_cursor"] is None

