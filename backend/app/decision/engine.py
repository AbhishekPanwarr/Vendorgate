"""Decision engine: pure functions (no I/O, clock, randomness)."""

from backend.app.core.hashing import canonical_json
from backend.app.core.hashing import sha256_hex
from backend.app.domain.enums import Awaiting
from backend.app.domain.enums import FixedBy
from backend.app.domain.enums import Outcome
from backend.app.domain.enums import Severity
from backend.app.domain.enums import Status
from backend.app.domain.enums import Tier
from backend.app.domain.models import Counterfactual
from backend.app.domain.models import Decision
from backend.app.domain.models import Finding
from backend.app.domain.models import Resolution
from backend.app.risk.scoring import score

ENGINE_VERSION = "1.0.0"
_STATUS_ORDER = {Status.APPROVED: 0, Status.PENDING: 1, Status.REJECTED: 2}


def _key(f: Finding) -> str:
    return f"{f.check_id}|{f.subject or ''}"


def apply_resolutions(findings: list[Finding], resolutions: list[Resolution]) -> list[Finding]:
    res = {(r.finding_key): r for r in resolutions}
    out = []
    for f in findings:
        r = res.get(_key(f))
        if r is None:
            out.append(f)
        elif r.action == "CLEARED":
            out.append(f.model_copy(update={"outcome": Outcome.WARN, "severity": Severity.INFO}))
        else:  # CONFIRMED
            out.append(
                f.model_copy(update={"outcome": Outcome.FAIL, "severity": Severity.CRITICAL})
            )
    return out


def is_blocking(f: Finding, policy: object) -> bool:
    if f.outcome == Outcome.FAIL:
        return True
    return bool(f.outcome == Outcome.UNVERIFIABLE and f.mandatory)


def approvers_for(tier: str, policy: object) -> list[str]:
    approvals = policy.raw["base"]["approvals"]  # type: ignore[attr-defined]
    if tier == "LOW":
        return []
    return list(approvals.get(tier, approvals.get("MEDIUM", ["CONTROLLER"])))


def _counterfactuals(findings: list[Finding], policy: object, risk: object) -> list[Counterfactual]:
    fixable = [f for f in findings if f.outcome == Outcome.FAIL and f.fixed_by == FixedBy.VENDOR]
    if not fixable:
        return []
    cfs = []
    for f in fixable:
        rest = [g for g in findings if g is not f]
        blocking_left = [g for g in rest if is_blocking(g, policy)]
        if not blocking_left:
            cfs.append(
                Counterfactual(
                    fix_set=[f.fix.code if f.fix else f.check_id],
                    status=Status.APPROVED,
                    tier=Tier.LOW,
                    score=0.0,
                    awaiting=set(),
                    score_delta=None,
                )
            )
        else:
            codes = sorted({g.reason_code or g.check_id for g in blocking_left})
            cfs.append(
                Counterfactual(
                    fix_set=[f.fix.code if f.fix else f.check_id],
                    status=Status.PENDING,
                    tier=Tier(risk.band.value) if hasattr(risk, "band") else Tier.MEDIUM,
                    score=float(risk.total),  # type: ignore[attr-defined]
                    awaiting={Awaiting.VENDOR},
                    score_delta=None,
                    note=f"still blocked by {', '.join(codes)}",
                )
            )
    return cfs


def decide(
    *,
    findings: list[Finding],
    resolutions: list[Resolution],
    submission_facts: object,
    policy: object,
) -> Decision:
    eff = apply_resolutions(findings, resolutions)
    eff = sorted(eff, key=_key)
    blocking = [f for f in eff if is_blocking(f, policy)]
    risk = score(eff, submission_facts)
    reason_codes = sorted({f.reason_code for f in blocking if f.reason_code})
    blocking_ids = [f.check_id for f in blocking]
    auto_max = float(policy.raw["base"]["scoring"]["auto_approve_max"])  # type: ignore[attr-defined]

    awaiting: set[Awaiting]
    if any(f.severity == Severity.CRITICAL and f.outcome == Outcome.FAIL for f in blocking):
        status, tier, awaiting = Status.REJECTED, Tier.BLOCKED, set()
    elif any(f.fixed_by == FixedBy.NONE and f.outcome == Outcome.FAIL for f in blocking):
        status, tier, awaiting = Status.REJECTED, Tier(risk.band.value), set()
    elif blocking:
        status, tier = Status.PENDING, Tier(risk.band.value)
        awaiting = {
            Awaiting(f.fixed_by.value)
            for f in blocking
            if f.fixed_by in (FixedBy.VENDOR, FixedBy.INTERNAL)
        }
    elif risk.band == Tier.LOW and risk.total <= auto_max:
        status, tier, awaiting = Status.APPROVED, Tier.LOW, set()
    else:
        status, tier, awaiting = Status.PENDING, Tier(risk.band.value), {Awaiting.INTERNAL}

    route: list[str] = []
    if status == Status.PENDING and Awaiting.INTERNAL in awaiting:
        # Show the full approval route upfront, even while vendor items are
        # still open (approvers act after vendor fixes land).
        if tier == Tier.LOW:
            route = ["AP_ANALYST"]
        else:
            route = approvers_for(tier.value, policy)

    cfs = (
        _counterfactuals(blocking, policy, risk)
        if (status == Status.PENDING and Awaiting.VENDOR in awaiting)
        else []
    )

    required = [f.fix for f in blocking if f.fix]
    repro = sha256_hex(
        canonical_json(
            {
                "findings": sorted(f.model_dump(mode="json").get("check_id", "") for f in eff),
                "policy": policy.version,  # type: ignore[attr-defined]
                "engine": ENGINE_VERSION,
            }
        )
    )
    d = Decision(
        status=status,
        awaiting=awaiting,
        tier=tier,
        score=risk,
        reason_codes=reason_codes,
        blocking_finding_ids=blocking_ids,
        required_actions=required,
        approval_route=route,
        counterfactuals=cfs,
        policy_version=policy.version,  # type: ignore[attr-defined]
        engine_version=ENGINE_VERSION,
        reproducibility_hash=repro,
    )
    assert not (d.status == Status.APPROVED and any(is_blocking(f, policy) for f in eff))
    return d


def counterfactuals(*args: object, **kwargs: object) -> list[Counterfactual]:
    raise NotImplementedError("use decide().counterfactuals")
