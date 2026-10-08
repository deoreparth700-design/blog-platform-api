"""
API Tests for Authentication and JWT Middleware (/api/auth-test).

Tests:
- missing Authorization header -> 401
- malformed Bearer token -> 401
- expired Bearer token -> 401
- invalid token signature -> 401
- valid Bearer token -> 200
- extracted userId returned correctly

Uses the REAL get_current_user dependency without mocking authentication.
"""

import time
import jwt
from tests.conftest import TEST_JWT_SECRET, USER_A_ID, USER_B_ID


def test_auth_missing_token_returns_401(client):
    """Request without Authorization header is rejected with 401."""
    resp = client.get("/api/auth-test")
    assert resp.status_code == 401
    assert "Not authenticated" in resp.json()["detail"]


def test_auth_malformed_token_returns_401(client, invalid_headers):
    """Malformed JWT string is rejected with 401."""
    resp = client.get("/api/auth-test", headers=invalid_headers)
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid authentication credentials"


def test_auth_expired_token_returns_401(client, expired_headers):
    """Expired JWT token is rejected with 401."""
    resp = client.get("/api/auth-test", headers=expired_headers)
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Token has expired"


def test_auth_invalid_signature_returns_401(client, user_a_id):
    """JWT signed with an unauthorized secret is rejected with 401."""
    tampered_token = jwt.encode(
        {"userId": user_a_id, "exp": int(time.time()) + 3600},
        "wrong-secret-key",
        algorithm="HS256"
    )
    resp = client.get("/api/auth-test", headers={"Authorization": f"Bearer {tampered_token}"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid authentication credentials"


def test_auth_valid_token_user_a(client, auth_headers):
    """Valid User A token succeeds with 200 and returns User A ID."""
    resp = client.get("/api/auth-test", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["authenticated"] is True
    assert body["userId"] == USER_A_ID


def test_auth_valid_token_user_b(client, user_b_headers):
    """Valid User B token succeeds with 200 and returns User B ID."""
    resp = client.get("/api/auth-test", headers=user_b_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["authenticated"] is True
    assert body["userId"] == USER_B_ID
