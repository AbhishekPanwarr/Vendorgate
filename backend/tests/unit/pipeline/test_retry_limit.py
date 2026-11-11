from backend.app.domain.enums import FixedBy
from backend.app.domain.enums import Outcome
from backend.app.domain.enums import Severity
from backend.app.domain.models import Evidence
from backend.app.domain.models import Finding


class _Ctx:
    def __init__(self, policy):
        self.policy = policy

    def value(self, path):
        return {
            "requester.expected_annual_spend_usd": 1000,
            "requester.category": "OFFICE_SUPPLIES",
            "company.country": "US",
            "bank.country": "US",
            "requester.one_time": "False",
            "requester.data_access": "False",
        }.get(path)


def _mk(code, sev=Severity.SOFT):
    return Finding(
        check_id="C-X",
        stage="S3",
        check_version=1,
        outcome=Outcome.FAIL,
        severity=sev,
        reason_code=code,
        title="t",
        detail="d",
        evidence=[Evidence(kind="claim", ref="c", summary="s")],
        fixed_by=FixedBy.VENDOR,
        deterministic=True,
        reads=[],
    )


def test_retry_counts_per_code_not_per_attempt():
    # alternating codes: A, B, A -> no code hits 3; 4th A -> limit
    from backend.app.core.policy import load_policy

    policy = load_policy("policy")
    from backend.app.persistence.store import append_case_event

    append_case_event("case-r", "attempt.recorded", {"reason_code": "A", "version": 1})
    append_case_event("case-r", "attempt.recorded", {"reason_code": "B", "version": 2})

    import asyncio

    class Ctx(_Ctx):
        case_id = "case-r"

    f = asyncio.run(_pol03(Ctx(policy), ["A"]))
    assert f == []  # A has 1 attempt < 3
    append_case_event("case-r", "attempt.recorded", {"reason_code": "A", "version": 3})
    append_case_event("case-r", "attempt.recorded", {"reason_code": "A", "version": 4})
    f = asyncio.run(_pol03(Ctx(policy), ["A", "B"]))
    assert [x.reason_code for x in f] == ["RETRY_LIMIT_EXCEEDED"]


async def _pol03(ctx, codes):
    from backend.app.pipeline.checks import dup as dupmod

    findings = []
    for c in codes:
        findings.append(_mk(c))
    # inject findings then call the check with a stub context carrying them
    ctx.findings = findings
    out = await dupmod.retry_limit(ctx)
    return out
