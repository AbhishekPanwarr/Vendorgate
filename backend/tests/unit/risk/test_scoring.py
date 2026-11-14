from backend.app.risk.scoring import score


class _Ctx:
    def __init__(self, policy, values):
        self.policy = policy
        self._values = values

    def value(self, path):
        return self._values.get(path)


def _ctx(
    policy,
    usd=18000,
    category="OFFICE_SUPPLIES",
    country="US",
    bank_country="US",
    one_time="False",
    data_access="False",
):
    return _Ctx(
        policy,
        {
            "requester.expected_annual_spend_usd": usd,
            "requester.category": category,
            "company.country": country,
            "bank.country": bank_country,
            "requester.one_time": one_time,
            "requester.data_access": data_access,
        },
    )


def test_hp1_anchor():
    from backend.app.core.policy import load_policy

    p = load_policy("policy")
    r = score([], _ctx(p))
    assert r.total == 7.5
    assert r.band.value == "LOW"
    assert r.components["SPEND"].points == 5.0
    assert r.components["BANK_ID"].points == 1.5
    assert r.components["CATEGORY"].points == 1.0


def test_worked_b_anchor():
    from backend.app.core.policy import load_policy
    from backend.app.domain.enums import Outcome
    from backend.app.domain.enums import Severity
    from backend.app.domain.models import Evidence
    from backend.app.domain.models import Finding

    p = load_policy("policy")
    ctx = _ctx(
        p, usd=120000, category="IT_SERVICES", country="IN", bank_country="IN", data_access="True"
    )
    findings = [
        Finding(
            check_id="C-CRD-01",
            stage="S5",
            check_version=1,
            outcome=Outcome.WARN,
            severity=Severity.INFO,
            reason_code="ENTITY_RECENT",
            title="t",
            detail="d",
            evidence=[Evidence(kind="claim", ref="c", summary="s")],
            score_tags={"REGISTRY_MEDIA": 0.2},
        )
    ]
    r = score(findings, ctx)
    assert r.total == 37.5
    assert r.band.value == "LOW"
