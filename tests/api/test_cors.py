"""
API Tests for CORS configuration and ALLOWED_ORIGINS handling.

Tests:
1. Unset ALLOWED_ORIGINS -> No Access-Control-Allow-Origin header for foreign origins.
2. Empty ALLOWED_ORIGINS or whitespace-only entries -> Disallows foreign origins.
3. Listed origin in ALLOWED_ORIGINS -> Access-Control-Allow-Origin present with that exact origin and credentials allowed.
4. Unlisted origin -> No Access-Control-Allow-Origin header.
5. Whitespace and trailing commas in ALLOWED_ORIGINS -> Cleanly trimmed and empty items ignored.
6. Wildcard origin "*" -> Access-Control-Allow-Origin is "*", but allow_credentials is never combined with wildcard.
7. parse_allowed_origins unit testing -> verifies parsing edge cases.
"""

from fastapi.testclient import TestClient
from src.app import create_app, parse_allowed_origins


def test_parse_allowed_origins_helper():
    assert parse_allowed_origins(None) == []
    assert parse_allowed_origins("") == []
    assert parse_allowed_origins("   ") == []
    assert parse_allowed_origins(" , , ") == []
    assert parse_allowed_origins("http://localhost:3000") == ["http://localhost:3000"]
    assert parse_allowed_origins("  http://localhost:3000 , http://localhost:5173 , ") == [
        "http://localhost:3000",
        "http://localhost:5173",
    ]


def test_cors_unset_disallows_foreign_origin(monkeypatch):
    """When ALLOWED_ORIGINS is unset, foreign Origin receives no Access-Control-Allow-Origin header."""
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    app = create_app()
    with TestClient(app) as client:
        # Simple GET request with foreign Origin
        res = client.get("/health", headers={"Origin": "http://evil.com"})
        assert res.status_code == 200
        assert "access-control-allow-origin" not in res.headers

        # Preflight OPTIONS request with foreign Origin
        res_opt = client.options(
            "/health",
            headers={
                "Origin": "http://evil.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" not in res_opt.headers


def test_cors_empty_disallows_foreign_origin(monkeypatch):
    """When ALLOWED_ORIGINS is empty or commas only, foreign Origin receives no Access-Control-Allow-Origin header."""
    monkeypatch.setenv("ALLOWED_ORIGINS", "  ,  ,  ")
    app = create_app()
    with TestClient(app) as client:
        res = client.get("/health", headers={"Origin": "http://localhost:3000"})
        assert res.status_code == 200
        assert "access-control-allow-origin" not in res.headers


def test_cors_listed_origin_allowed(monkeypatch):
    """When an origin is in ALLOWED_ORIGINS, header is present with that exact origin and credentials allowed."""
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")
    app = create_app()
    with TestClient(app) as client:
        res = client.get("/health", headers={"Origin": "http://localhost:3000"})
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert res.headers.get("access-control-allow-credentials") == "true"

        # Preflight
        res_preflight = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert res_preflight.status_code == 200
        assert res_preflight.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert res_preflight.headers.get("access-control-allow-credentials") == "true"


def test_cors_unlisted_origin_disallowed(monkeypatch):
    """When an origin is not in ALLOWED_ORIGINS, no Access-Control-Allow-Origin header is returned."""
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")
    app = create_app()
    with TestClient(app) as client:
        res = client.get("/health", headers={"Origin": "http://untrusted-domain.com"})
        assert res.status_code == 200
        assert "access-control-allow-origin" not in res.headers


def test_cors_whitespace_and_trailing_commas_handled(monkeypatch):
    """Whitespace and trailing commas in ALLOWED_ORIGINS are trimmed and empty entries ignored."""
    monkeypatch.setenv(
        "ALLOWED_ORIGINS",
        "   http://localhost:3000  ,  http://localhost:5173   ,   ",
    )
    app = create_app()
    with TestClient(app) as client:
        # First listed origin
        res1 = client.get("/health", headers={"Origin": "http://localhost:3000"})
        assert res1.status_code == 200
        assert res1.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert res1.headers.get("access-control-allow-credentials") == "true"

        # Second listed origin
        res2 = client.get("/health", headers={"Origin": "http://localhost:5173"})
        assert res2.status_code == 200
        assert res2.headers.get("access-control-allow-origin") == "http://localhost:5173"
        assert res2.headers.get("access-control-allow-credentials") == "true"

        # Foreign origin rejected
        res_foreign = client.get("/health", headers={"Origin": "http://not-in-list.com"})
        assert "access-control-allow-origin" not in res_foreign.headers


def test_cors_wildcard_origin_never_allows_credentials(monkeypatch):
    """When wildcard '*' is configured, allow_credentials is never True."""
    monkeypatch.setenv("ALLOWED_ORIGINS", "*")
    app = create_app()
    with TestClient(app) as client:
        res = client.get("/health", headers={"Origin": "http://example.com"})
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") == "*"
        assert res.headers.get("access-control-allow-credentials") is None
