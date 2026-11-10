import pytest
from pydantic import ValidationError

from backend.app.domain.enums import FixedBy
from backend.app.domain.enums import Outcome
from backend.app.domain.enums import Severity
from backend.app.domain.enums import Source
from backend.app.domain.enums import Status
from backend.app.domain.enums import Tier
from backend.app.domain.models import Decision
from backend.app.domain.models import Evidence
from backend.app.domain.models import Finding
from backend.app.domain.models import RiskBreakdown


def _ev():
    return Evidence(kind="claim", ref="c1", summary="s")


def test_finding_minimal():
    f = Finding(
        check_id="C-X", stage="S3", check_version=1, outcome=Outcome.PASS, title="t", detail="d"
    )
    assert f.outcome == Outcome.PASS


def test_finding_fail_no_evidence_raises():
    with pytest.raises(ValidationError):
        Finding(
            check_id="C-X",
            stage="S3",
            check_version=1,
            outcome=Outcome.FAIL,
            severity=Severity.HARD,
            reason_code="R",
            title="t",
            detail="d",
        )


def test_finding_fail_no_reason_raises():
    with pytest.raises(ValidationError):
        Finding(
            check_id="C-X",
            stage="S3",
            check_version=1,
            outcome=Outcome.FAIL,
            severity=Severity.HARD,
            title="t",
            detail="d",
            evidence=[_ev()],
        )


def test_decision_approved_nonempty_awaiting_raises():
    rb = RiskBreakdown(components={}, total=10.0, band=Tier.LOW)
    with pytest.raises(ValidationError):
        Decision(
            status=Status.APPROVED,
            awaiting={"VENDOR"},
            tier=Tier.LOW,
            score=rb,
            policy_version="v",
            engine_version="e",
            reproducibility_hash="h",
        )


def test_risk_total_bounds():
    with pytest.raises(ValidationError):
        RiskBreakdown(components={}, total=101.0, band=Tier.LOW)
    assert RiskBreakdown(components={}, total=0.0, band=Tier.LOW).total == 0.0


def test_finding_fail_none_fixedby_ok():
    f = Finding(
        check_id="C-X",
        stage="S3",
        check_version=1,
        outcome=Outcome.FAIL,
        severity=Severity.HARD,
        reason_code="R",
        title="t",
        detail="d",
        evidence=[_ev()],
        fixed_by=FixedBy.NONE,
    )
    assert f.fixed_by == FixedBy.NONE
    assert Source.FORM.value == "FORM"
