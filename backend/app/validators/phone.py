"""Phone + postal validators."""

import re

import phonenumbers

from backend.app.validators.base import ValidationResult

_US_ZIP_RE = re.compile(r"^\d{5}(-\d{4})?$")
_IN_PIN_RE = re.compile(r"^[1-9]\d{5}$")
_GB_POST_RE = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$", re.IGNORECASE)
_DE_PLZ_RE = re.compile(r"^\d{5}$")


def validate_phone(value: str, country: str) -> ValidationResult:
    try:
        num = phonenumbers.parse(value, country)
    except Exception:
        return ValidationResult(valid=False, reason="BAD_STRUCTURE")
    if not phonenumbers.is_possible_number(num):
        return ValidationResult(valid=False, reason="BAD_STRUCTURE")
    e164 = phonenumbers.format_in_original_format(num, country)
    e164 = phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
    return ValidationResult(valid=True, normalized=e164)


def validate_postal(value: str, country: str) -> ValidationResult:
    s = (value or "").strip()
    c = (country or "").upper()
    ok = (
        bool(_US_ZIP_RE.match(s))
        if c == "US"
        else bool(_IN_PIN_RE.match(s))
        if c == "IN"
        else bool(_GB_POST_RE.match(s))
        if c == "GB"
        else bool(_DE_PLZ_RE.match(s))
        if c == "DE"
        else len(s) > 0
    )
    if not ok:
        return ValidationResult(valid=False, reason="BAD_STRUCTURE")
    return ValidationResult(valid=True, normalized=s.upper())
