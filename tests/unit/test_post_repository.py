"""
Unit Tests for PostRepository (src/repositories/post_repository.py).

Tests the LEFT JOIN query in get_post_by_id:
- Post with multiple comments: returns post dict with comments list ordered by created_at, id
- Post with no comments: LEFT JOIN NULL comment row is skipped, returns comments: []
- Post not found: returns None
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4
from datetime import datetime, timezone
import pytest

from src.repositories.post_repository import PostRepository


@pytest.fixture
def mock_pool_and_connection():
    dummy_pool = MagicMock()
    mock_conn = AsyncMock()
    
    # Pool acquire context manager returns mock_conn
    mock_acquire_cm = MagicMock()
    mock_acquire_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_cm.__aexit__ = AsyncMock(return_value=None)
    dummy_pool.acquire.return_value = mock_acquire_cm
    
    return dummy_pool, mock_conn


@pytest.mark.asyncio
async def test_get_post_by_id_with_comments_left_join(mock_pool_and_connection):
    """get_post_by_id processes multiple LEFT JOIN rows into a single post with comments list."""
    dummy_pool, mock_conn = mock_pool_and_connection
    repo = PostRepository(dummy_pool)
    
    author_id = uuid4()
    commenter_id = uuid4()
    now = datetime.now(timezone.utc)
    
    mock_rows = [
        {
            "id": 1,
            "author_id": author_id,
            "title": "Post Title",
            "content": "Post Content",
            "created_at": now,
            "updated_at": now,
            "comment_id": 101,
            "comment_post_id": 1,
            "comment_author_id": commenter_id,
            "comment_content": "First comment",
            "comment_created_at": now,
        },
        {
            "id": 1,
            "author_id": author_id,
            "title": "Post Title",
            "content": "Post Content",
            "created_at": now,
            "updated_at": now,
            "comment_id": 102,
            "comment_post_id": 1,
            "comment_author_id": commenter_id,
            "comment_content": "Second comment",
            "comment_created_at": now,
        },
    ]
    mock_conn.fetch.return_value = mock_rows

    result = await repo.get_post_by_id(1)

    assert result is not None
    assert result["id"] == 1
    assert result["title"] == "Post Title"
    assert len(result["comments"]) == 2
    assert result["comments"][0]["id"] == 101
    assert result["comments"][0]["content"] == "First comment"
    assert result["comments"][1]["id"] == 102
    assert result["comments"][1]["content"] == "Second comment"


@pytest.mark.asyncio
async def test_get_post_by_id_without_comments_left_join(mock_pool_and_connection):
    """get_post_by_id skips NULL comment row from LEFT JOIN and returns comments: []."""
    dummy_pool, mock_conn = mock_pool_and_connection
    repo = PostRepository(dummy_pool)
    
    author_id = uuid4()
    now = datetime.now(timezone.utc)
    
    mock_rows = [
        {
            "id": 2,
            "author_id": author_id,
            "title": "Solo Post",
            "content": "No comments here",
            "created_at": now,
            "updated_at": now,
            "comment_id": None,
            "comment_post_id": None,
            "comment_author_id": None,
            "comment_content": None,
            "comment_created_at": None,
        }
    ]
    mock_conn.fetch.return_value = mock_rows

    result = await repo.get_post_by_id(2)

    assert result is not None
    assert result["id"] == 2
    assert result["title"] == "Solo Post"
    assert result["comments"] == []


@pytest.mark.asyncio
async def test_get_post_by_id_not_found_returns_none(mock_pool_and_connection):
    """get_post_by_id returns None when query produces no rows."""
    dummy_pool, mock_conn = mock_pool_and_connection
    repo = PostRepository(dummy_pool)
    
    mock_conn.fetch.return_value = []

    result = await repo.get_post_by_id(999)

    assert result is None
