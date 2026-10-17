from typing import Any, Optional
from fastapi import HTTPException, status

MAX_INT32 = 2147483647


def parse_user_id(value: Any) -> int:
    """
    Parse and validate user ID from authentication token.
    Accepts positive integers or string of ASCII digits within signed 32-bit integer range (1 <= id <= 2147483647).
    Raises HTTPException(401, "Invalid user token") for anything else
    (None, bool, float, non-digit string, non-ascii, <= 0, > 2147483647).
    """
    if isinstance(value, bool) or value is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parsed: Optional[int] = None

    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str) and value.isascii() and value.isdigit():
        parsed = int(value)

    if parsed is not None and 1 <= parsed <= MAX_INT32:
        return parsed

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid user token",
        headers={"WWW-Authenticate": "Bearer"},
    )
