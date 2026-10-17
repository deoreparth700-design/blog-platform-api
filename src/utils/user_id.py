from typing import Any
from fastapi import HTTPException, status

def parse_user_id(value: Any) -> int:
    """
    Parse and validate user ID from authentication token.
    Accepts positive integers or string of digits representing positive integers.
    Raises HTTPException(401, "Invalid user token") for anything else
    (None, bool, float, non-digit string, <= 0).
    """
    if isinstance(value, bool) or value is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if isinstance(value, int):
        if value <= 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return value

    if isinstance(value, str):
        if value.isdigit():
            parsed = int(value)
            if parsed > 0:
                return parsed

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid user token",
        headers={"WWW-Authenticate": "Bearer"},
    )
