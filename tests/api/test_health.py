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


def test_cors_headers(client):
    """CORS preflight or request returns proper allow-origin and credentials policy."""
    response = client.options(
        "/health",
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "*"
    assert response.headers.get("access-control-allow-credentials") is None
