import json

from backend.app.core.policy import load_policy
from backend.app.decision import engine
from backend.tests.golden.test_invariants import _Ctx

POLICY = load_policy("policy")


def test_decision_determinism_100():
    import random

    from backend.app.domain.enums import FixedBy
    from backend.app.domain.enums import Outcome
    from backend.app.domain.enums import Severity
    from backend.app.domain.models import Evidence
    from backend.app.domain.models import Finding

    random.seed(42)
    f = [
        Finding(
            check_id=f"C-{i}",
            stage="S3",
            check_version=1,
            outcome=random.choice([Outcome.PASS, Outcome.WARN, Outcome.FAIL]),
            severity=Severity.SOFT,
            reason_code="R",
            title="t",
            detail="d",
            evidence=[Evidence(kind="claim", ref="c", summary="s")],
            fixed_by=FixedBy.VENDOR,
        )
        for i in range(8)
    ]
    first = None
    for _ in range(100):
        d = engine.decide(findings=list(f), resolutions=[], submission_facts=_Ctx(), policy=POLICY)
        dump = json.dumps(d.model_dump(mode="json"), sort_keys=True)
        if first is None:
            first = dump
        assert dump == first


def test_counterfactual_monotonicity():
    from backend.app.domain.enums import Status

    with open("backend/tests/golden/fixtures/ec-1-run-1.json") as fh:
        fx = json.load(fh)
    d = fx["decision"]
    assert d["status"] == "PENDING"
    assert any(c["status"] == "APPROVED" for c in d["counterfactuals"])
    order = {Status.APPROVED: 0, Status.PENDING: 1, Status.REJECTED: 2}
    for c in d["counterfactuals"]:
        assert order[Status(c["status"])] <= order[Status(d["status"])]
