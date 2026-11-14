"""US EIN + ABA validators."""

import re

from backend.app.validators.base import ValidationResult

_EIN_RE = re.compile(r"^\d{2}-?\d{7}$")
_VALID_EIN_PREFIXES = {
    "01",
    "02",
    "03",
    "04",
    "05",
    "06",
    "10",
    "11",
    "12",
    "13",
    "14",
    "15",
    "16",
    "20",
    "21",
    "22",
    "23",
    "24",
    "25",
    "26",
    "27",
    "30",
    "32",
    "33",
    "34",
    "35",
    "36",
    "37",
    "38",
    "39",
    "40",
    "41",
    "42",
    "43",
    "44",
    "45",
    "46",
    "47",
    "48",
    "50",
    "51",
    "52",
    "53",
    "54",
    "55",
    "56",
    "57",
    "58",
    "59",
    "60",
    "61",
    "62",
    "63",
    "64",
    "65",
    "66",
    "68",
    "71",
    "72",
    "73",
    "74",
    "75",
    "76",
    "77",
    "80",
    "81",
    "82",
    "83",
    "84",
    "85",
    "86",
    "87",
    "88",
    "90",
    "91",
    "92",
    "93",
    "94",
    "95",
    "98",
    "99",
}


def validate_ein(value: str) -> ValidationResult:
    s = (value or "").strip()
    digits = s.replace("-", "")
    if not _EIN_RE.match(s):
        return ValidationResult(valid=False, reason="BAD_STRUCTURE")
    if digits[:2] not in _VALID_EIN_PREFIXES:
        return ValidationResult(valid=False, reason="UNKNOWN_PREFIX")
    return ValidationResult(valid=True, normalized=f"{digits[:2]}-{digits[2:]}")


def aba_valid(routing: str) -> bool:
    r = (routing or "").strip()
    if len(r) != 9 or not r.isdigit():
        return False
    d = [int(c) for c in r]
    return (3 * (d[0] + d[3] + d[6]) + 7 * (d[1] + d[4] + d[7]) + (d[2] + d[5] + d[8])) % 10 == 0


def validate_aba(value: str) -> ValidationResult:
    s = (value or "").strip()
    if len(s) != 9 or not s.isdigit():
        return ValidationResult(valid=False, reason="BAD_STRUCTURE")
    if not aba_valid(s):
        return ValidationResult(valid=False, reason="BAD_CHECKSUM")
    return ValidationResult(valid=True, normalized=s)
