from backend.app.domain.enums import Awaiting
from backend.app.domain.enums import DocType
from backend.app.domain.enums import FixedBy
from backend.app.domain.enums import Outcome
from backend.app.domain.enums import RunMode
from backend.app.domain.enums import Severity
from backend.app.domain.enums import Source
from backend.app.domain.enums import Status
from backend.app.domain.enums import SubmissionType
from backend.app.domain.enums import Tier


def test_outcome_values():
    assert [o.value for o in Outcome] == ["PASS", "WARN", "FAIL", "UNVERIFIABLE", "SKIPPED", "NA"]
    assert len(Outcome) == 6


def test_severity_ordering():
    assert Severity.INFO < Severity.SOFT < Severity.HARD < Severity.CRITICAL


def test_fixedby():
    assert [f.value for f in FixedBy] == ["VENDOR", "INTERNAL", "NONE"]


def test_status():
    assert [s.value for s in Status] == ["APPROVED", "PENDING", "REJECTED"]


def test_tier():
    assert [t.value for t in Tier] == ["LOW", "MEDIUM", "HIGH", "BLOCKED"]


def test_source():
    assert [s.value for s in Source] == [
        "FORM",
        "DOC",
        "REGISTRY",
        "BANK",
        "SCREENING",
        "SYSTEM",
        "LLM",
    ]


def test_doctype():
    assert DocType.W9.value == "W9"
    assert len(DocType) == 11


def test_misc():
    assert [s.value for s in SubmissionType] == ["NEW_VENDOR", "CHANGE_REQUEST"]
    assert [a.value for a in Awaiting] == ["VENDOR", "INTERNAL"]
    assert [m.value for m in RunMode] == ["FULL", "DELTA"]
