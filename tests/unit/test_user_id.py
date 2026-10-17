"""
Unit tests for user ID parsing helper (src/utils/user_id.py).

Validates:
- Positive integers return int (e.g. 3 -> 3)
- Digit strings representing positive integers return int (e.g. "3" -> 3)
- Invalid types or values raise HTTPException 401 ("Invalid user token"):
  - None
  - bool (True, False)
  - float (e.g. 3.5)
  - non-digit string (e.g. "abc", "12a")
  - non-positive integers (0, -1)
  - non-positive numeric strings ("0", "-1")
"""

import pytest
from fastapi import HTTPException

from src.utils.user_id import parse_user_id


def test_parse_user_id_positive_int():
    assert parse_user_id(3) == 3
    assert parse_user_id(1) == 1
    assert parse_user_id(999999) == 999999


def test_parse_user_id_digit_string():
    assert parse_user_id("3") == 3
    assert parse_user_id("1") == 1
    assert parse_user_id("42") == 42


@pytest.mark.parametrize(
    "invalid_val",
    [
        "abc",
        None,
        0,
        -1,
        True,
        False,
        3.5,
        "0",
        "-1",
        "12.5",
        "",
        [],
        {},
    ],
)
def test_parse_user_id_invalid_values_raise_401(invalid_val):
    with pytest.raises(HTTPException) as exc_info:
        parse_user_id(invalid_val)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid user token"
