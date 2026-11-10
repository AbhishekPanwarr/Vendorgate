"""GB VAT + DE USt-IdNr validators (own implementation; stdnum is the test oracle)."""

import re

from backend.app.validators.base import ValidationResult

_GB_VAT_RE = re.compile(r"^GB(\d{9}|\d{12})$")
_DE_VAT_RE = re.compile(r"^DE[1-9]\d{8}$")


def _gb_weights_ok(digits9: str) -> bool:
    weights = (8, 7, 6, 5, 4, 3, 2, 10, 1)
    c = sum(w * int(n) for w, n in zip(weights, digits9, strict=True)) % 97
    if int(digits9[:3]) >= 100:
        return c in (0, 42, 55)
    return c == 0


def _gb_check(digits: str) -> bool:
    return _gb_weights_ok(digits[:9])


def validate_gb_vat(value: str) -> ValidationResult:
    s = (value or "").replace(" ", "").upper()
    if not _GB_VAT_RE.match(s):
        return ValidationResult(valid=False, reason="BAD_STRUCTURE")
    if not _gb_check(s[2:]):
        return ValidationResult(valid=False, reason="BAD_CHECKSUM")
    return ValidationResult(valid=True, normalized=s)


def _de_check(digits: str) -> bool:
    # ISO 7064 MOD 11,10: valid iff running checksum over all 9 digits == 1
    check = 5
    for ch in digits:
        check = (((check or 10) * 2) % 11 + int(ch)) % 10
    return check == 1


def validate_de_vat(value: str) -> ValidationResult:
    s = (value or "").replace(" ", "").upper()
    if not _DE_VAT_RE.match(s):
        return ValidationResult(valid=False, reason="BAD_STRUCTURE")
    if not _de_check(s[2:]):
        return ValidationResult(valid=False, reason="BAD_CHECKSUM")
    return ValidationResult(valid=True, normalized=s)


def validate_vat(value: str, country: str) -> ValidationResult:
    c = (country or "").upper()
    if c == "GB":
        return validate_gb_vat(value)
    if c == "DE":
        return validate_de_vat(value)
    return ValidationResult(valid=False, reason="WRONG_COUNTRY_SHAPE")
