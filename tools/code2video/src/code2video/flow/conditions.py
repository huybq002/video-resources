"""Đánh giá điều kiện trên state của flow."""
from __future__ import annotations

from typing import Any

OPS = ("eq", "ne", "gt", "lt", "in", "exists", "missing")
MISSING = object()


def lookup(state: dict, path: str) -> Any:
    """Lấy giá trị theo đường dẫn a.b.c; trả MISSING nếu thiếu."""
    current: Any = state
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return MISSING
    return current


def evaluate(condition: dict | None, state: dict) -> bool:
    """Thiếu condition = luôn đúng; field thiếu → False (trừ op missing)."""
    if not condition:
        return True
    op = condition.get("op")
    if op not in OPS:
        raise ValueError(f"Toán tử điều kiện không hợp lệ: {op}")
    value = lookup(state, str(condition.get("field", "")))
    if op == "missing":
        return value is MISSING
    if value is MISSING:
        return False
    if op == "exists":
        return True
    expected = condition.get("value")
    try:
        if op == "eq":
            return value == expected
        if op == "ne":
            return value != expected
        if op == "gt":
            return value > expected
        if op == "lt":
            return value < expected
        return value in expected
    except TypeError:
        return False
