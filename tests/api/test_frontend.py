"""
API Tests for the frontend UI served at GET /app.

Tests:
- GET /app returns 200 OK
- Response Content-Type includes text/html
- Response body contains the expected frontend index.html content
"""


def test_serve_frontend_endpoint(client):
    """GET /app returns 200 OK with text/html content-type and valid HTML."""
    response = client.get("/app")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert b"<!DOCTYPE html>" in response.content
    assert b"Blog Platform" in response.content
    assert b"AUTH_URL" in response.content
