from enum import StrEnum
from enum import IntEnum


class Outcome(StrEnum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    UNVERIFIABLE = "UNVERIFIABLE"
    SKIPPED = "SKIPPED"
    NA = "NA"


class Severity(IntEnum):
    INFO = 0
    SOFT = 1
    HARD = 2
    CRITICAL = 3


class FixedBy(StrEnum):
    VENDOR = "VENDOR"
    INTERNAL = "INTERNAL"
    NONE = "NONE"


class Status(StrEnum):
    APPROVED = "APPROVED"
    PENDING = "PENDING"
    REJECTED = "REJECTED"


class Tier(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    BLOCKED = "BLOCKED"


class Source(StrEnum):
    FORM = "FORM"
    DOC = "DOC"
    REGISTRY = "REGISTRY"
    BANK = "BANK"
    SCREENING = "SCREENING"
    SYSTEM = "SYSTEM"
    LLM = "LLM"


class DocType(StrEnum):
    W9 = "W9"
    W8BEN = "W8BEN"
    W8BENE = "W8BENE"
    GST_CERT = "GST_CERT"
    VAT_CERT = "VAT_CERT"
    INCORP_CERT = "INCORP_CERT"
    BANK_LETTER = "BANK_LETTER"
    VOIDED_CHEQUE = "VOIDED_CHEQUE"
    COI = "COI"
    TRADE_LICENSE = "TRADE_LICENSE"
    UNKNOWN = "UNKNOWN"


class SubmissionType(StrEnum):
    NEW_VENDOR = "NEW_VENDOR"
    CHANGE_REQUEST = "CHANGE_REQUEST"


class Awaiting(StrEnum):
    VENDOR = "VENDOR"
    INTERNAL = "INTERNAL"


class RunMode(StrEnum):
    FULL = "FULL"
    DELTA = "DELTA"
