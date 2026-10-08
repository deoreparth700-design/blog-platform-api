"""
Unit Tests for Pydantic Schemas (src/schemas/).

Tests:
- PostCreate, PostUpdate, PostResponse, PaginatedPostResponse
- CommentCreate, CommentUpdate, CommentResponse
- LikeCountResponse
Valid instances and meaningful invalid inputs (missing required fields, wrong types).
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4
import pytest
from pydantic import ValidationError

from src.schemas.post import PostCreate, PostUpdate, PostResponse, PaginatedPostResponse
from src.schemas.comment import CommentCreate, CommentUpdate, CommentResponse
from src.schemas.like import LikeCountResponse


# ---------------------------------------------------------------------------
# Post Schemas
# ---------------------------------------------------------------------------
def test_post_create_valid():
    """PostCreate accepts valid title and content."""
    post = PostCreate(title="Test Title", content="Test Content")
    assert post.title == "Test Title"
    assert post.content == "Test Content"


def test_post_create_missing_required_fields():
    """PostCreate rejects missing title or content."""
    with pytest.raises(ValidationError):
        PostCreate(title="Only Title")  # missing content

    with pytest.raises(ValidationError):
        PostCreate(content="Only Content")  # missing title


def test_post_update_valid_partial():
    """PostUpdate allows partial or full updates, defaulting fields to None."""
    # Title only
    up1 = PostUpdate(title="New Title")
    assert up1.title == "New Title"
    assert up1.content is None

    # Content only
    up2 = PostUpdate(content="New Content")
    assert up2.title is None
    assert up2.content == "New Content"

    # Both
    up3 = PostUpdate(title="Both", content="Both Content")
    assert up3.title == "Both"
    assert up3.content == "Both Content"

    # Empty update
    up4 = PostUpdate()
    assert up4.title is None
    assert up4.content is None


def test_post_response_valid():
    """PostResponse correctly serializes post records including UUIDs and timestamps."""
    author_uuid = uuid4()
    now = datetime.now(timezone.utc)
    res = PostResponse(
        id=1,
        author_id=author_uuid,
        title="Valid Title",
        content="Valid Content",
        created_at=now,
        updated_at=now,
    )
    assert res.id == 1
    assert res.author_id == author_uuid
    assert res.title == "Valid Title"


def test_post_response_invalid_uuid():
    """PostResponse rejects invalid UUID string for author_id."""
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        PostResponse(
            id=1,
            author_id="not-a-valid-uuid",
            title="Title",
            content="Content",
            created_at=now,
            updated_at=now,
        )


def test_paginated_post_response_valid():
    """PaginatedPostResponse correctly serializes items and pagination metadata."""
    author_uuid = uuid4()
    now = datetime.now(timezone.utc)
    item = PostResponse(
        id=1,
        author_id=author_uuid,
        title="Title",
        content="Content",
        created_at=now,
        updated_at=now,
    )
    paginated = PaginatedPostResponse(
        items=[item],
        page=1,
        limit=10,
        total=1,
        total_pages=1,
    )
    assert paginated.page == 1
    assert paginated.limit == 10
    assert paginated.total == 1
    assert paginated.total_pages == 1
    assert len(paginated.items) == 1


# ---------------------------------------------------------------------------
# Comment Schemas
# ---------------------------------------------------------------------------
def test_comment_create_valid():
    """CommentCreate accepts valid content."""
    comment = CommentCreate(content="Great article!")
    assert comment.content == "Great article!"


def test_comment_create_missing_content():
    """CommentCreate rejects missing content."""
    with pytest.raises(ValidationError):
        CommentCreate()


def test_comment_update_valid():
    """CommentUpdate allows optional content update."""
    up1 = CommentUpdate(content="Updated content")
    assert up1.content == "Updated content"

    up2 = CommentUpdate()
    assert up2.content is None


def test_comment_response_valid():
    """CommentResponse validates author UUID, post ID, and created timestamp."""
    author_uuid = uuid4()
    now = datetime.now(timezone.utc)
    res = CommentResponse(
        id=10,
        post_id=5,
        author_id=author_uuid,
        content="Nice post",
        created_at=now,
    )
    assert res.id == 10
    assert res.post_id == 5
    assert res.author_id == author_uuid
    assert res.content == "Nice post"


def test_comment_response_invalid_author_id():
    """CommentResponse rejects invalid author UUID."""
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        CommentResponse(
            id=10,
            post_id=5,
            author_id="invalid-uuid",
            content="Nice post",
            created_at=now,
        )


# ---------------------------------------------------------------------------
# Like Schemas
# ---------------------------------------------------------------------------
def test_like_count_response_valid():
    """LikeCountResponse serializes post_id and like_count."""
    res = LikeCountResponse(post_id=42, like_count=15)
    assert res.post_id == 42
    assert res.like_count == 15


def test_like_count_response_invalid_types():
    """LikeCountResponse rejects non-integer like_count."""
    with pytest.raises(ValidationError):
        LikeCountResponse(post_id=42, like_count="not-an-int")
