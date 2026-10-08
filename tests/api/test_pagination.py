"""
API Tests for Pagination on GET /api/posts/.

Tests:
- default page (1) and default limit (10)
- custom page (page=2)
- custom limit (limit=5)
- multiple pages with total and total_pages calculations
- validation constraints:
  - page < 1 -> 422
  - limit < 1 -> 422
  - limit > 100 -> 422
- deterministic response schema validation (items, page, limit, total, total_pages)
"""

from uuid import UUID
from datetime import datetime, timezone
import pytest

from src.app import app
from src.routes.posts import get_post_service, get_cache_service
from tests.conftest import USER_A_ID


def make_post(post_id: int):
    return {
        "id": post_id,
        "author_id": UUID(USER_A_ID),
        "title": f"Post {post_id}",
        "content": f"Content {post_id}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def test_pagination_defaults(client, fake_cache_service, mock_post_service):
    """GET /api/posts/ without query params defaults to page=1 and limit=10."""
    mock_post_service.get_posts.return_value = {
        "items": [make_post(1)],
        "page": 1,
        "limit": 10,
        "total": 1,
        "total_pages": 1,
    }
    app.dependency_overrides[get_post_service] = lambda: mock_post_service
    app.dependency_overrides[get_cache_service] = lambda: fake_cache_service

    resp = client.get("/api/posts/")
    assert resp.status_code == 200
    mock_post_service.get_posts.assert_awaited_once_with(1, 10)
    data = resp.json()
    assert data["page"] == 1
    assert data["limit"] == 10
    assert data["total"] == 1
    assert data["total_pages"] == 1


def test_pagination_custom_page_and_limit(client, fake_cache_service, mock_post_service):
    """GET /api/posts/ accepts explicit page and limit parameters."""
    mock_post_service.get_posts.return_value = {
        "items": [make_post(6), make_post(7)],
        "page": 2,
        "limit": 5,
        "total": 12,
        "total_pages": 3,
    }
    app.dependency_overrides[get_post_service] = lambda: mock_post_service
    app.dependency_overrides[get_cache_service] = lambda: fake_cache_service

    resp = client.get("/api/posts/?page=2&limit=5")
    assert resp.status_code == 200
    mock_post_service.get_posts.assert_awaited_once_with(2, 5)
    data = resp.json()
    assert data["page"] == 2
    assert data["limit"] == 5
    assert data["total"] == 12
    assert data["total_pages"] == 3
    assert len(data["items"]) == 2


def test_pagination_multiple_pages_metadata(client, fake_cache_service, mock_post_service):
    """Response accurately includes items array, total, and total_pages."""
    mock_post_service.get_posts.return_value = {
        "items": [make_post(i) for i in range(1, 11)],
        "page": 1,
        "limit": 10,
        "total": 45,
        "total_pages": 5,
    }
    app.dependency_overrides[get_post_service] = lambda: mock_post_service
    app.dependency_overrides[get_cache_service] = lambda: fake_cache_service

    resp = client.get("/api/posts/?page=1&limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 45
    assert data["total_pages"] == 5
    assert len(data["items"]) == 10


def test_pagination_page_less_than_one_returns_422(client, fake_cache_service, mock_post_service):
    """page=0 violates ge=1 constraint and returns 422."""
    app.dependency_overrides[get_post_service] = lambda: mock_post_service
    app.dependency_overrides[get_cache_service] = lambda: fake_cache_service

    resp = client.get("/api/posts/?page=0&limit=10")
    assert resp.status_code == 422


def test_pagination_page_negative_returns_422(client, fake_cache_service, mock_post_service):
    """page=-5 violates ge=1 constraint and returns 422."""
    app.dependency_overrides[get_post_service] = lambda: mock_post_service
    app.dependency_overrides[get_cache_service] = lambda: fake_cache_service

    resp = client.get("/api/posts/?page=-5&limit=10")
    assert resp.status_code == 422


def test_pagination_limit_less_than_one_returns_422(client, fake_cache_service, mock_post_service):
    """limit=0 violates ge=1 constraint and returns 422."""
    app.dependency_overrides[get_post_service] = lambda: mock_post_service
    app.dependency_overrides[get_cache_service] = lambda: fake_cache_service

    resp = client.get("/api/posts/?page=1&limit=0")
    assert resp.status_code == 422


def test_pagination_limit_exceeding_max_returns_422(client, fake_cache_service, mock_post_service):
    """limit=101 violates le=100 constraint and returns 422."""
    app.dependency_overrides[get_post_service] = lambda: mock_post_service
    app.dependency_overrides[get_cache_service] = lambda: fake_cache_service

    resp = client.get("/api/posts/?page=1&limit=101")
    assert resp.status_code == 422


def test_pagination_limit_upper_boundary_100_accepted(client, fake_cache_service, mock_post_service):
    """limit=100 is within boundary and succeeds."""
    mock_post_service.get_posts.return_value = {
        "items": [],
        "page": 1,
        "limit": 100,
        "total": 0,
        "total_pages": 0,
    }
    app.dependency_overrides[get_post_service] = lambda: mock_post_service
    app.dependency_overrides[get_cache_service] = lambda: fake_cache_service

    resp = client.get("/api/posts/?page=1&limit=100")
    assert resp.status_code == 200
    mock_post_service.get_posts.assert_awaited_once_with(1, 100)
