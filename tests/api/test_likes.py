"""
API Tests for Likes Endpoints (/api/posts/{post_id}/like and /api/posts/{post_id}/likes).

Tests:
- POST /api/posts/{post_id}/like:
  - like post -> 201
  - missing auth -> 401
  - duplicate like -> 409
  - missing post -> 404
- DELETE /api/posts/{post_id}/like:
  - unlike post -> 204
  - missing auth -> 401
  - unlike non-existent like -> 404
  - missing post -> 404
- GET /api/posts/{post_id}/likes:
  - get like count -> 200
  - missing post -> 404
"""

import pytest
from fastapi import HTTPException, status

from src.app import app
from src.routes.likes import get_like_service


# ---------------------------------------------------------------------------
# POST /api/posts/{post_id}/like (Like Post)
# ---------------------------------------------------------------------------
def test_like_post_success(client, auth_headers, mock_like_service):
    """Authenticated user likes post -> 201 Created."""
    mock_like_service.like_post.return_value = {"message": "Post liked", "post_id": 1}
    app.dependency_overrides[get_like_service] = lambda: mock_like_service

    resp = client.post("/api/posts/1/like", headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["message"] == "Post liked"


def test_like_post_missing_auth_returns_401(client, mock_like_service):
    """Liking a post without token returns 401 Unauthorized."""
    app.dependency_overrides[get_like_service] = lambda: mock_like_service

    resp = client.post("/api/posts/1/like")
    assert resp.status_code == 401


def test_like_post_duplicate_returns_409(client, auth_headers, mock_like_service):
    """Liking an already liked post returns 409 Conflict."""
    mock_like_service.like_post.side_effect = HTTPException(
        status_code=status.HTTP_409_CONFLICT, detail="Post already liked"
    )
    app.dependency_overrides[get_like_service] = lambda: mock_like_service

    resp = client.post("/api/posts/1/like", headers=auth_headers)
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Post already liked"


def test_like_post_missing_post_returns_404(client, auth_headers, mock_like_service):
    """Liking a non-existent post returns 404 Not Found."""
    mock_like_service.like_post.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
    )
    app.dependency_overrides[get_like_service] = lambda: mock_like_service

    resp = client.post("/api/posts/999/like", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Post not found"


# ---------------------------------------------------------------------------
# DELETE /api/posts/{post_id}/like (Unlike Post)
# ---------------------------------------------------------------------------
def test_unlike_post_success(client, auth_headers, mock_like_service):
    """Authenticated user unlikes post -> 204 No Content."""
    mock_like_service.unlike_post.return_value = None
    app.dependency_overrides[get_like_service] = lambda: mock_like_service

    resp = client.delete("/api/posts/1/like", headers=auth_headers)
    assert resp.status_code == 204


def test_unlike_post_missing_auth_returns_401(client, mock_like_service):
    """Unliking a post without token returns 401 Unauthorized."""
    app.dependency_overrides[get_like_service] = lambda: mock_like_service

    resp = client.delete("/api/posts/1/like")
    assert resp.status_code == 401


def test_unlike_post_nonexistent_like_returns_404(client, auth_headers, mock_like_service):
    """Unliking a post that wasn't liked returns 404 Not Found."""
    mock_like_service.unlike_post.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Like not found"
    )
    app.dependency_overrides[get_like_service] = lambda: mock_like_service

    resp = client.delete("/api/posts/1/like", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Like not found"


def test_unlike_post_missing_post_returns_404(client, auth_headers, mock_like_service):
    """Unliking on a non-existent post returns 404 Not Found."""
    mock_like_service.unlike_post.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
    )
    app.dependency_overrides[get_like_service] = lambda: mock_like_service

    resp = client.delete("/api/posts/999/like", headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/posts/{post_id}/likes (Get Like Count)
# ---------------------------------------------------------------------------
def test_get_like_count_success(client, mock_like_service):
    """GET like count returns 200 with post_id and like_count."""
    mock_like_service.get_like_count.return_value = {"post_id": 1, "like_count": 5}
    app.dependency_overrides[get_like_service] = lambda: mock_like_service

    resp = client.get("/api/posts/1/likes")
    assert resp.status_code == 200
    data = resp.json()
    assert data["post_id"] == 1
    assert data["like_count"] == 5


def test_get_like_count_missing_post_returns_404(client, mock_like_service):
    """GET like count on non-existent post returns 404 Not Found."""
    mock_like_service.get_like_count.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
    )
    app.dependency_overrides[get_like_service] = lambda: mock_like_service

    resp = client.get("/api/posts/999/likes")
    assert resp.status_code == 404
