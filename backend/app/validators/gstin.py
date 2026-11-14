"""GSTIN / PAN / IFSC validators (IN)."""

import re

from backend.app.validators.base import ValidationResult

_C = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_VALID_STATES = {f"{i:02d}" for i in range(1, 38)} - {"00"}

_GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
_PAN_RE = re.compile(r"^[A-Z]{5}\d{4}[A-Z]$")
_IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")


def gstin_check_char(first14: str) -> str:
    total = 0
    for i, ch in enumerate(first14):
        p = _C.index(ch) * (1 if i % 2 == 0 else 2)
        total += p // 36 + p % 36
    return _C[(36 - total % 36) % 36]


def validate_gstin(value: str) -> ValidationResult:
    s = (value or "").strip().upper()
    if len(s) != 15:
        return ValidationResult(valid=False, reason="BAD_LENGTH")
    if not _GSTIN_RE.match(s):
        return ValidationResult(valid=False, reason="BAD_STRUCTURE")
    if s[:2] not in _VALID_STATES:
        return ValidationResult(valid=False, reason="UNKNOWN_STATE")
    if gstin_check_char(s[:14]) != s[14]:
        return ValidationResult(valid=False, reason="BAD_CHECKSUM")
    return ValidationResult(valid=True, normalized=s, details={"pan": s[2:12], "state": s[:2]})


def validate_pan(value: str) -> ValidationResult:
    s = (value or "").strip().upper()
    if len(s) != 10:
        return ValidationResult(valid=False, reason="BAD_LENGTH")
    if not _PAN_RE.match(s):
        return ValidationResult(valid=False, reason="BAD_CHARSET")
    return ValidationResult(valid=True, normalized=s, details={"entity": s[3]})


def validate_ifsc(value: str) -> ValidationResult:
    s = (value or "").strip().upper()
    if len(s) != 11:
        return ValidationResult(valid=False, reason="BAD_LENGTH")
    if not _IFSC_RE.match(s):
        return ValidationResult(valid=False, reason="BAD_STRUCTURE")
    return ValidationResult(valid=True, normalized=s)
