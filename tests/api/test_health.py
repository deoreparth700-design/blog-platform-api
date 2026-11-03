"""
API Tests for /health endpoint.

Tests:
- GET /health returns 200 OK
- Response payload structure and status message
"""


def test_health_check_endpoint(client):
    """GET /health returns 200 with standard health status payload."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["message"] == "Blog Platform API is running"


def test_cors_disallowed_by_default_when_unset(client):
    """When ALLOWED_ORIGINS is unset, foreign Origin receives no Access-Control-Allow-Origin header."""
    response = client.get(
        "/health",
        headers={"Origin": "http://example.com"},
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
