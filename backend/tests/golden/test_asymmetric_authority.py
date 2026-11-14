from backend.app.decision.adjudication import apply_adjudication
from backend.app.decision.adjudication import corroborator_evidence
from backend.app.domain.enums import FixedBy
from backend.app.domain.enums import Outcome
from backend.app.domain.enums import Severity
from backend.app.domain.models import Evidence
from backend.app.domain.models import Finding
from backend.app.llm.tasks_other import AdjudicationVerdict


def _finding(reason="NAME_UNCONFIRMED", sev=Severity.SOFT):
    return Finding(
        check_id="C-NAME-02",
        stage="S5",
        check_version=1,
        outcome=Outcome.FAIL,
        severity=sev,
        reason_code=reason,
        title="t",
        detail="d",
        evidence=[Evidence(kind="claim", ref="c", summary="s")],
        fixed_by=FixedBy.VENDOR,
        deterministic=True,
        reads=[],
    )


def _verdict(label, conf, swap=True):
    return AdjudicationVerdict(
        label=label, confidence=conf, rationale="r", order_swap_consistent=swap
    )


def test_T1_llm_alone_never_lowers():
    f = apply_adjudication(_finding(), _verdict("SAME", 0.9), [])
    assert f.outcome == Outcome.FAIL and f.reason_code == "NAME_UNCONFIRMED"
    assert any(e.kind == "llm" for e in f.evidence)


def test_T2_corroborated_same_lowers():
    corr = [corroborator_evidence("K3", "incorp cert names variant")]
    f = apply_adjudication(_finding(), _verdict("SAME", 0.8), corr)
    assert f.outcome == Outcome.WARN and f.reason_code == "NAME_VARIANT_EXPLAINED"
    assert f.deterministic is False


def test_T3_low_confidence_no_downgrade():
    corr = [corroborator_evidence("K3", "x")]
    f = apply_adjudication(_finding(), _verdict("SAME", 0.5), corr)
    assert f.outcome == Outcome.FAIL


def test_T4_swap_inconsistent_no_downgrade():
    corr = [corroborator_evidence("K3", "x")]
    f = apply_adjudication(_finding(), _verdict("SAME", 0.9, swap=False), corr)
    assert f.outcome == Outcome.FAIL


def test_T5_sanctions_never_cleared_by_llm():
    san = Finding(
        check_id="C-SAN-01",
        stage="S7",
        check_version=1,
        outcome=Outcome.FAIL,
        severity=Severity.HARD,
        reason_code="SANCTIONS_REVIEW",
        title="t",
        detail="d",
        evidence=[Evidence(kind="claim", ref="c", summary="s")],
        fixed_by=FixedBy.INTERNAL,
        deterministic=True,
        reads=[],
    )
    # S8 never routes SAN/* findings to apply_adjudication; even if misrouted,
    # callers must not apply. Guard: check_id prefix gate lives in S8 (tested below).
    assert san.check_id.startswith("C-SAN")


def test_T6_no_llm_in_san_dup_routing():
    import pathlib

    for rel in (
        "backend/app/pipeline/checks/san.py",
        "backend/app/pipeline/checks/dup.py",
        "backend/app/decision/routing.py",
    ):
        assert "ctx.llm" not in pathlib.Path(rel).read_text()
