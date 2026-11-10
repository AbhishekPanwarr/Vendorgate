from hypothesis import given
from hypothesis import strategies as st

from backend.app.core.policy import load_policy
from backend.app.domain.enums import FixedBy
from backend.app.domain.enums import Outcome
from backend.app.domain.enums import Severity
from backend.app.domain.models import Evidence
from backend.app.domain.models import Finding
from backend.app.risk.scoring import score
from backend.app.risk.tiers import band
from backend.tests.unit.risk.test_scoring import _ctx

POLICY = load_policy("policy")


@given(st.floats(min_value=0, max_value=10**9, allow_nan=False))
def test_total_bounded(usd):
    r = score([], _ctx(POLICY, usd=usd))
    assert 0 <= r.total <= 100


@given(st.integers(min_value=0, max_value=5))
def test_tags_never_lower(n):
    ctx = _ctx(POLICY)
    base = score([], ctx).total
    findings = [
        Finding(
            check_id=f"C-{i}",
            stage="S3",
            check_version=1,
            outcome=Outcome.FAIL,
            severity=Severity.SOFT,
            reason_code="R",
            title="t",
            detail="d",
            evidence=[Evidence(kind="claim", ref="c", summary="s")],
            fixed_by=FixedBy.VENDOR,
            score_tags={"BANK_ID": 0.1},
        )
        for i in range(n)
    ]
    assert score(findings, ctx).total >= base


def test_band_edges():
    assert band(39.98, POLICY) == "LOW"
    assert band(39.99, POLICY) == "MEDIUM"
    assert band(75.0, POLICY) == "HIGH"
