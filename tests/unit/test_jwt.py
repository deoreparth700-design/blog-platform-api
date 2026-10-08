"""
Unit Tests for JWT Utilities (src/utils/jwt_utils.py).

Covers:
- valid token decoding
- expired token rejection (401)
- malformed token rejection (401)
- invalid signature rejection (401)
- missing userId in payload rejection (401)
- missing JWT_ACCESS_SECRET configuration rejection (401)
"""

import time
import pytest
import jwt
from fastapi import HTTPException

from src.utils.jwt_utils import verify_jwt_token
from tests.conftest import TEST_JWT_SECRET, USER_A_ID


def test_verify_valid_jwt_token():
    """Valid token successfully returns decoded payload with userId."""
    payload = {
        "userId": USER_A_ID,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")
    decoded = verify_jwt_token(token)

    assert decoded["userId"] == USER_A_ID
    assert "exp" in decoded
    assert "iat" in decoded


def test_verify_expired_jwt_token():
    """Expired token raises HTTPException with 401 status and expiration detail."""
    payload = {
        "userId": USER_A_ID,
        "iat": int(time.time()) - 7200,
        "exp": int(time.time()) - 3600,
    }
    token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")

    with pytest.raises(HTTPException) as exc_info:
        verify_jwt_token(token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token has expired"


def test_verify_malformed_jwt_token():
    """Malformed token string raises HTTPException with 401 status."""
    malformed_token = "not.a.valid.jwt.token"

    with pytest.raises(HTTPException) as exc_info:
        verify_jwt_token(malformed_token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid authentication credentials"


def test_verify_invalid_signature_jwt_token():
    """Token signed with wrong secret raises HTTPException with 401 status."""
    payload = {
        "userId": USER_A_ID,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    token_wrong_secret = jwt.encode(payload, "completely-wrong-secret", algorithm="HS256")

    with pytest.raises(HTTPException) as exc_info:
        verify_jwt_token(token_wrong_secret)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid authentication credentials"


def test_verify_missing_user_id_in_payload():
    """Token missing the required 'userId' claim raises HTTPException with 401 status."""
    payload = {
        "email": "test@example.com",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")

    with pytest.raises(HTTPException) as exc_info:
        verify_jwt_token(token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid token structure"


def test_verify_missing_jwt_secret_configuration(monkeypatch):
    """When JWT_ACCESS_SECRET is unset, verify_jwt_token raises 401 configuration error."""
    monkeypatch.delenv("JWT_ACCESS_SECRET", raising=False)
    payload = {"userId": USER_A_ID, "exp": int(time.time()) + 3600}
    token = jwt.encode(payload, "any-key", algorithm="HS256")

    with pytest.raises(HTTPException) as exc_info:
        verify_jwt_token(token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Authentication configuration error"
