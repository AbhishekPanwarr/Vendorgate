"""Decision invariants I1-I5 — green in Phase 1 (markers removed)."""

import random

from backend.app.core.policy import load_policy
from backend.app.decision import engine
from backend.app.domain.enums import FixedBy
from backend.app.domain.enums import Outcome
from backend.app.domain.enums import Severity
from backend.app.domain.enums import Status
from backend.app.domain.models import Evidence
from backend.app.domain.models import Finding

POLICY = load_policy("policy")


class _Ctx:
    policy = POLICY

    def value(self, path: str):  # noqa: ANN001, ANN202
        defaults = {
            "requester.expected_annual_spend_usd": 1000,
            "requester.category": "OFFICE_SUPPLIES",
            "requester.one_time": "False",
            "requester.data_access": "False",
            "company.country": "US",
            "bank.country": "US",
        }
        return defaults.get(path)


def _mk(
    outcome: Outcome,
    severity: Severity = Severity.SOFT,
    mandatory: bool = True,
    fixed_by: FixedBy = FixedBy.VENDOR,
    kind: str = "claim",
) -> Finding:
    return Finding(
        check_id="C-T",
        stage="S3",
        check_version=1,
        outcome=outcome,
        severity=severity,
        reason_code="R" if outcome == Outcome.FAIL else None,
        title="t",
        detail="d",
        evidence=[Evidence(kind=kind, ref="c", summary="s")],  # type: ignore[arg-type]
        fixed_by=fixed_by,
        mandatory=mandatory,
        deterministic=True,
        reads=[],
    )


def _rand_findings(n=5):
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
                mandatory=True,
                deterministic=True,
                reads=[],
            )
        )
    return out


def test_I1_approved_only_clean():
    for _ in range(50):
        findings = [f for f in _rand_findings() if f.outcome != Outcome.FAIL]
        d = engine.decide(findings=findings, resolutions=[], submission_facts=_Ctx(), policy=POLICY)
        if d.status == Status.APPROVED:
            assert not [f for f in findings if engine.is_blocking(f, POLICY)]


def test_I2_critical_rejects():
    for _ in range(50):
        f = _rand_findings()
        f.append(_mk(Outcome.FAIL, Severity.CRITICAL))
        d = engine.decide(findings=f, resolutions=[], submission_facts=_Ctx(), policy=POLICY)
        assert d.status == Status.REJECTED and d.tier.value == "BLOCKED"


def test_I3_deterministic_order_independent():
    for _ in range(50):
        f = _rand_findings()
        kw = dict(resolutions=[], submission_facts=_Ctx(), policy=POLICY)
        d1 = engine.decide(findings=f, **kw)  # type: ignore[arg-type]
        d2 = engine.decide(findings=list(reversed(f)), **kw)  # type: ignore[arg-type]
        assert d1.model_dump() == d2.model_dump()
        d3 = engine.decide(findings=list(f), **kw)  # type: ignore[arg-type]
        assert d1.model_dump() == d3.model_dump()


def test_I4_removal_never_worsens():
    order = {Status.APPROVED: 0, Status.PENDING: 1, Status.REJECTED: 2}
    for _ in range(50):
        f = _rand_findings()
        base = engine.decide(findings=f, resolutions=[], submission_facts=_Ctx(), policy=POLICY)
        blocking = [g for g in f if engine.is_blocking(g, POLICY)]
        if not blocking:
            continue
        g = random.choice(blocking)
        rest = [x for x in f if x is not g]
        d2 = engine.decide(findings=rest, resolutions=[], submission_facts=_Ctx(), policy=POLICY)
        assert order[d2.status] <= order[base.status]


def test_I5_llm_needs_corroborator():
    lone = _mk(Outcome.FAIL, Severity.SOFT, kind="llm")
    d = engine.decide(findings=[lone], resolutions=[], submission_facts=_Ctx(), policy=POLICY)
    assert d.status != Status.APPROVED
    corroborated = lone.model_copy(
        update={
            "evidence": [
                Evidence(kind="llm", ref="c", summary="s"),
                Evidence(kind="claim", ref="r", summary="registry"),
            ]
        }
    )
    d2 = engine.decide(
        findings=[corroborated], resolutions=[], submission_facts=_Ctx(), policy=POLICY
    )
    assert d2.status != Status.APPROVED  # decide() alone never downgrades; adjudication does
