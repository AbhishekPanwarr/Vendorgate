"""Shared ValidationResult."""

from typing import Literal

from pydantic import BaseModel

Reason = Literal[
    "BAD_LENGTH",
    "BAD_CHARSET",
    "BAD_STRUCTURE",
    "BAD_CHECKSUM",
    "UNKNOWN_PREFIX",
    "UNKNOWN_STATE",
    "WRONG_COUNTRY_SHAPE",
]


class ValidationResult(BaseModel):
    valid: bool
    reason: Reason | None = None
    normalized: str | None = None
    details: dict[str, object] = {}
