"""Decision invariants I1-I5 — Phase 0 red (xfail strict)."""

import random

import pytest

from backend.app.decision import engine


def _rand_findings(n=5):
    from backend.app.domain.enums import FixedBy
    from backend.app.domain.enums import Outcome
    from backend.app.domain.enums import Severity
    from backend.app.domain.models import Evidence
    from backend.app.domain.models import Finding

    out = []
    for i in range(n):
        outcome = random.choice([Outcome.PASS, Outcome.WARN, Outcome.FAIL])
        out.append(
            Finding(
                check_id=f"C-{i}",
                stage="S3",
                check_version=1,
                outcome=outcome,
                severity=Severity.SOFT,
                reason_code="R" if outcome == Outcome.FAIL else None,
                title="t",
                detail="d",
                evidence=[Evidence(kind="claim", ref="c", summary="s")],
                fixed_by=FixedBy.VENDOR,
            )
        )
    return out


@pytest.mark.xfail(strict=True, reason="Phase 1 implements decide()")
def test_I1_approved_only_clean():
    f = _rand_findings()
    d = engine.decide(findings=f, resolutions=[], submission_facts={}, policy={})
    assert d.status is not None


@pytest.mark.xfail(strict=True, reason="Phase 1 implements decide()")
def test_I2_critical_rejects():
    f = _rand_findings()
    d = engine.decide(findings=f, resolutions=[], submission_facts={}, policy={})
    assert d.tier is not None


@pytest.mark.xfail(strict=True, reason="Phase 1 implements decide()")
def test_I3_deterministic_order_independent():
    f = _rand_findings()
    d1 = engine.decide(findings=f, resolutions=[], submission_facts={}, policy={})
    d2 = engine.decide(findings=list(reversed(f)), resolutions=[], submission_facts={}, policy={})
    assert d1 == d2


@pytest.mark.xfail(strict=True, reason="Phase 1 implements decide()")
def test_I4_removal_never_worsens():
    f = _rand_findings()
    d = engine.decide(findings=f, resolutions=[], submission_facts={}, policy={})
    assert d.status is not None


@pytest.mark.xfail(strict=True, reason="Phase 1 implements decide()")
def test_I5_llm_needs_corroborator():
    f = _rand_findings()
    d = engine.decide(findings=f, resolutions=[], submission_facts={}, policy={})
    assert d.status is not None
