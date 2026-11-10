"""IBAN + SWIFT validators."""

import re

from backend.app.validators.base import ValidationResult

IBAN_LEN = {
    "GB": 22,
    "DE": 22,
    "FR": 27,
    "IT": 27,
    "ES": 24,
    "NL": 18,
    "IE": 22,
    "US": 0,
    "IN": 0,
}
# BBAN structure per country (mirrors stdnum strictness for oracle agreement)
IBAN_BBAN = {
    "GB": re.compile(r"^[A-Z]{4}\d{14}$"),
    "DE": re.compile(r"^\d{18}$"),
    "FR": re.compile(r"^\d{23}$"),
    "IT": re.compile(r"^[A-Z]\d{5}\d{5}[A-Z0-9]{12}$"),
    "ES": re.compile(r"^\d{20}$"),
    "NL": re.compile(r"^[A-Z]{4}\d{10}$"),
    "IE": re.compile(r"^[A-Z0-9]{4}\d{14}$"),
}
_SWIFT_RE = re.compile(r"^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$")


def iban_valid(value: str) -> bool:
    s = (value or "").replace(" ", "").upper()
    if len(s) < 4:
        return False
    expected = IBAN_LEN.get(s[:2])
    if not expected or len(s) != expected:
        return False
    rearr = s[4:] + s[:4]
    try:
        num = "".join(str(int(c, 36)) for c in rearr)
    except ValueError:
        return False
    return int(num) % 97 == 1


def validate_iban(value: str) -> ValidationResult:
    s = (value or "").replace(" ", "").upper()
    if len(s) < 4 or not s[:2].isalpha():
        return ValidationResult(valid=False, reason="BAD_STRUCTURE")
    expected = IBAN_LEN.get(s[:2])
    if not expected:
        return ValidationResult(valid=False, reason="WRONG_COUNTRY_SHAPE")
    if len(s) != expected:
        return ValidationResult(valid=False, reason="BAD_LENGTH")
    bban = IBAN_BBAN.get(s[:2])
    if bban and not bban.match(s[4:]):
        return ValidationResult(valid=False, reason="BAD_STRUCTURE")
    if not iban_valid(s):
        return ValidationResult(valid=False, reason="BAD_CHECKSUM")
    return ValidationResult(valid=True, normalized=s)


def validate_swift(value: str) -> ValidationResult:
    s = (value or "").strip().upper()
    if len(s) not in (8, 11):
        return ValidationResult(valid=False, reason="BAD_LENGTH")
    if not _SWIFT_RE.match(s):
        return ValidationResult(valid=False, reason="BAD_CHARSET")
    return ValidationResult(valid=True, normalized=s, details={"country": s[4:6]})
