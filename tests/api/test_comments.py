"""
API Tests for Comments Endpoints (/api/posts/{post_id}/comments and /api/comments/{comment_id}).

Tests:
- POST /api/posts/{post_id}/comments:
  - authenticated create -> 201
  - missing auth -> 401
  - malformed request -> 422
  - parent post missing -> 404
- GET /api/posts/{post_id}/comments:
  - list comments -> 200
  - parent post missing -> 404
- PUT /api/comments/{comment_id}:
  - update owner -> 200
  - missing auth -> 401
  - non-owner -> 403
  - missing comment -> 404
- DELETE /api/comments/{comment_id}:
  - delete owner -> 204
  - missing auth -> 401
  - non-owner -> 403
  - missing comment -> 404
"""

from uuid import UUID
from datetime import datetime, timezone
import pytest
from fastapi import HTTPException, status

from src.app import app
from src.routes.comments import get_comment_service
from tests.conftest import USER_A_ID, USER_B_ID


def make_comment_payload(comment_id: int = 1, post_id: int = 1, author_id: str = USER_A_ID, content: str = "Test comment"):
    return {
        "id": comment_id,
        "post_id": post_id,
        "author_id": UUID(author_id),
        "content": content,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# POST /api/posts/{post_id}/comments (Create Comment)
# ---------------------------------------------------------------------------
def test_create_comment_authenticated_success(client, auth_headers, mock_comment_service):
    """Authenticated user creates a comment successfully -> 201."""
    mock_comment_service.create_comment.return_value = make_comment_payload(1, 1, USER_A_ID, "Awesome post!")
    app.dependency_overrides[get_comment_service] = lambda: mock_comment_service

    resp = client.post("/api/posts/1/comments", json={"content": "Awesome post!"}, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["content"] == "Awesome post!"


def test_create_comment_missing_auth_returns_401(client, mock_comment_service):
    """Creating a comment without token returns 401."""
    app.dependency_overrides[get_comment_service] = lambda: mock_comment_service

    resp = client.post("/api/posts/1/comments", json={"content": "No auth"})
    assert resp.status_code == 401


def test_create_comment_malformed_body_returns_422(client, auth_headers, mock_comment_service):
    """Creating a comment with missing content field returns 422."""
    app.dependency_overrides[get_comment_service] = lambda: mock_comment_service

    resp = client.post("/api/posts/1/comments", json={}, headers=auth_headers)
    assert resp.status_code == 422


def test_create_comment_parent_post_missing_returns_404(client, auth_headers, mock_comment_service):
    """Creating a comment on a non-existent post returns 404."""
    mock_comment_service.create_comment.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
    )
    app.dependency_overrides[get_comment_service] = lambda: mock_comment_service

    resp = client.post("/api/posts/999/comments", json={"content": "Ghost"}, headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Post not found"


# ---------------------------------------------------------------------------
# GET /api/posts/{post_id}/comments (List Comments)
# ---------------------------------------------------------------------------
def test_get_comments_success(client, mock_comment_service):
    """GET comments for a post returns list of comments -> 200."""
    mock_comment_service.get_comments_by_post_id.return_value = [
        make_comment_payload(1, 1, content="Comment 1"),
        make_comment_payload(2, 1, content="Comment 2"),
    ]
    app.dependency_overrides[get_comment_service] = lambda: mock_comment_service

    resp = client.get("/api/posts/1/comments")
    assert resp.status_code == 200
    comments = resp.json()
    assert len(comments) == 2
    assert comments[0]["content"] == "Comment 1"


def test_get_comments_missing_parent_post_returns_404(client, mock_comment_service):
    """GET comments on a non-existent post returns 404."""
    mock_comment_service.get_comments_by_post_id.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
    )
    app.dependency_overrides[get_comment_service] = lambda: mock_comment_service

    resp = client.get("/api/posts/999/comments")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/comments/{comment_id} (Update Comment)
# ---------------------------------------------------------------------------
def test_update_comment_owner_success(client, auth_headers, mock_comment_service):
    """Comment owner updates comment -> 200."""
    updated = make_comment_payload(1, 1, USER_A_ID, "Edited comment")
    mock_comment_service.update_comment.return_value = updated
    app.dependency_overrides[get_comment_service] = lambda: mock_comment_service

    resp = client.put("/api/comments/1", json={"content": "Edited comment"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["content"] == "Edited comment"


def test_update_comment_missing_auth_returns_401(client, mock_comment_service):
    """Updating comment without token returns 401."""
    app.dependency_overrides[get_comment_service] = lambda: mock_comment_service

    resp = client.put("/api/comments/1", json={"content": "Update"})
    assert resp.status_code == 401


def test_update_comment_non_owner_returns_403(client, user_b_headers, mock_comment_service):
    """Non-owner updating comment returns 403 Forbidden."""
    mock_comment_service.update_comment.side_effect = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this comment"
    )
    app.dependency_overrides[get_comment_service] = lambda: mock_comment_service

    resp = client.put("/api/comments/1", json={"content": "Malicious edit"}, headers=user_b_headers)
    assert resp.status_code == 403


def test_update_comment_missing_returns_404(client, auth_headers, mock_comment_service):
    """Updating non-existent comment returns 404."""
    mock_comment_service.update_comment.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found"
    )
    app.dependency_overrides[get_comment_service] = lambda: mock_comment_service

    resp = client.put("/api/comments/999", json={"content": "Edit"}, headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/comments/{comment_id} (Delete Comment)
# ---------------------------------------------------------------------------
def test_delete_comment_owner_success(client, auth_headers, mock_comment_service):
    """Comment owner deletes comment -> 204 No Content."""
    mock_comment_service.delete_comment.return_value = True
    app.dependency_overrides[get_comment_service] = lambda: mock_comment_service

    resp = client.delete("/api/comments/1", headers=auth_headers)
    assert resp.status_code == 204


def test_delete_comment_missing_auth_returns_401(client, mock_comment_service):
    """Deleting comment without token returns 401."""
    app.dependency_overrides[get_comment_service] = lambda: mock_comment_service

    resp = client.delete("/api/comments/1")
    assert resp.status_code == 401


def test_delete_comment_non_owner_returns_403(client, user_b_headers, mock_comment_service):
    """Non-owner deleting comment returns 403 Forbidden."""
    mock_comment_service.delete_comment.side_effect = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this comment"
    )
    app.dependency_overrides[get_comment_service] = lambda: mock_comment_service

    resp = client.delete("/api/comments/1", headers=user_b_headers)
    assert resp.status_code == 403


def test_delete_comment_missing_returns_404(client, auth_headers, mock_comment_service):
    """Deleting non-existent comment returns 404."""
    mock_comment_service.delete_comment.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found"
    )
    app.dependency_overrides[get_comment_service] = lambda: mock_comment_service

    resp = client.delete("/api/comments/999", headers=auth_headers)
    assert resp.status_code == 404
