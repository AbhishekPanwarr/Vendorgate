"""S6 dedupe: C-DUP-01..06 (registry-backed, no LLM)."""

from typing import Any

from backend.app.domain.enums import FixedBy
from backend.app.domain.enums import Outcome
from backend.app.domain.enums import Severity
from backend.app.domain.models import Finding
from backend.app.domain.models import FixAction
from backend.app.matching.name_compare import compare_names
from backend.app.matching.name_compare import parse_name
from backend.app.network import graph as net
from backend.app.pipeline.checks._util import make_finding
from backend.app.pipeline.checks._util import sstr
from backend.app.pipeline.registry import check


def _submitter_bank_key(ctx: Any) -> str:
    country = sstr(ctx.value("bank.country"))
    acct = "".join(ch for ch in sstr(ctx.value("bank.account_number")) if ch.isdigit())
    routing = sstr(
        ctx.value("bank.routing_number")
        or sstr(ctx.value("bank.ifsc"))
        or sstr(ctx.value("bank.swift_bic"))
    )
    return net.bank_key(country, routing, acct)


def _name_rel(ctx: Any, other_name: str) -> str:
    cfg = dict(ctx.policy.raw["base"]["matching"]["name"])
    legal = sstr(ctx.value("company.legal_name"))
    return compare_names(parse_name(legal), parse_name(other_name), cfg).relation


@check(id="C-DUP-01", stage="S6", version=2, mandatory=True, reads=("tax.tax_id", "tax.country", "company.legal_name", "existing_vendor_id"))
async def tin_reuse(ctx: Any) -> list[Finding]:
    tin = sstr(ctx.value("tax.tax_id"))
    existing = str(ctx.value("existing_vendor_id") or "") or None
    hits = net.find_tin_reuse(tin, exclude=existing)
    if not hits:
        return []
    other = hits[0]
    rel = _name_rel(ctx, str(other["legal_name"]))
    if rel in ("EXACT", "EQUIVALENT"):
        return [
            make_finding(
                ctx,
                "C-DUP-01",
                "S6",
                1,
                outcome=Outcome.FAIL,
                severity=Severity.HARD,
                reason_code="DUPLICATE_EXISTING",
                title="Vendor already registered",
                detail=f"Already registered as {other['vendor_id']}; "
                "file a change request instead.",
                claim_paths=["tax.tax_id"],
                fixed_by=FixedBy.NONE,
            )
        ]
    if rel == "CORE_FUZZY":
        return [
            make_finding(
                ctx,
                "C-DUP-01",
                "S6",
                1,
                outcome=Outcome.FAIL,
                severity=Severity.HARD,
                reason_code="DUPLICATE_REVIEW",
                title="Possible duplicate vendor",
                detail="Same tax ID, similar name; analyst review.",
                claim_paths=["tax.tax_id"],
                fixed_by=FixedBy.INTERNAL,
            )
        ]
    return [
        make_finding(
            ctx,
            "C-DUP-01",
            "S6",
            1,
            outcome=Outcome.FAIL,
            severity=Severity.CRITICAL,
            reason_code="TIN_REUSE_DIFFERENT_NAME",
            title="Tax ID reused under a different name",
            detail="Identity fraud pattern; compliance hold.",
            claim_paths=["tax.tax_id"],
            fixed_by=FixedBy.NONE,
        )
    ]


@check(
    id="C-DUP-02",
    stage="S6",
    version=2,
    mandatory=True,
    reads=(
        "bank.account_number",
        "bank.country",
        "bank.routing_number",
        "bank.ifsc",
        "bank.swift_bic",
        "existing_vendor_id",
    ),
)
async def bank_reuse(ctx: Any) -> list[Finding]:
    existing = str(ctx.value("existing_vendor_id") or "") or None
    hits = net.find_bank_reuse(_submitter_bank_key(ctx), exclude=existing)
    if not hits:
        return []
    return [
        make_finding(
            ctx,
            "C-DUP-02",
            "S6",
            1,
            outcome=Outcome.FAIL,
            severity=Severity.CRITICAL,
            reason_code="BANK_SHARED_ACROSS_VENDORS",
            title="Bank account shared across vendors",
            detail=f"Account already used by {hits[0]['vendor_id']}.",
            claim_paths=["bank.account_number"],
            fixed_by=FixedBy.NONE,
        )
    ]


@check(
    id="C-DUP-05",
    stage="S6",
    version=2,
    mandatory=True,
    reads=("bank.account_number", "bank.country", "existing_vendor_id"),
)
async def bank_change(ctx: Any) -> list[Finding]:
    existing = str(ctx.value("existing_vendor_id") or "")
    if not existing:
        return []
    return [
        make_finding(
            ctx,
            "C-DUP-05",
            "S6",
            1,
            outcome=Outcome.FAIL,
            severity=Severity.HARD,
            reason_code="BANK_CHANGE_REQUIRES_CALLBACK",
            title="Bank change requires independent callback",
            detail="New bank details need callback verification.",
            claim_paths=["bank.account_number"],
            fix=FixAction(code="RECORD_CALLBACK", field_paths=["bank.account_number"]),
            fixed_by=FixedBy.INTERNAL,
            score_tags={"BANK_ID": 0.3},
        )
    ]


@check(
    id="C-DUP-03",
    stage="S6",
    version=1,
    mandatory=True,
    reads=("company.legal_name", "company.primary_contact.phone"),
)
async def near_duplicate(ctx: Any) -> list[Finding]:
    from backend.app.matching.similarity import core_similarity

    legal = sstr(ctx.value("company.legal_name"))
    phone = sstr(ctx.value("company.primary_contact.phone"))
    for vid, v in net.VENDORS.items():
        sim = core_similarity(legal.lower(), str(v.get("name_core", "")).lower())
        if sim >= 0.90 or (sim >= 0.80 and phone and phone == v.get("phone")):
            return [
                make_finding(
                    ctx,
                    "C-DUP-03",
                    "S6",
                    1,
                    outcome=Outcome.FAIL,
                    severity=Severity.HARD,
                    reason_code="DUPLICATE_REVIEW",
                    title="Near-duplicate vendor",
                    detail=f"Similar to {vid}; analyst review.",
                    claim_paths=["company.legal_name"],
                    fixed_by=FixedBy.INTERNAL,
                )
            ]
    return []


@check(
    id="C-DUP-04", stage="S6", version=1, mandatory=False, reads=("company.primary_contact.phone",)
)
async def attr_cluster(ctx: Any) -> list[Finding]:
    from backend.app.persistence import repo

    phone = sstr(ctx.value("company.primary_contact.phone"))
    cases = [{"case_id": c.get("case_id"), "phone": ""} for c in repo.STORE["cases"].values()]
    g = net.build_graph([{"case_id": "new", "phone": phone}] + cases)
    comp: set[Any] = next(
        (c for c in __import__("networkx").connected_components(g) if "new" in c), set()
    )
    vendors = [n for n in comp if not n.startswith(("phone:", "domain:"))]
    if len(vendors) >= 3:
        return [
            make_finding(
                ctx,
                "C-DUP-04",
                "S6",
                1,
                outcome=Outcome.FAIL,
                severity=Severity.HARD,
                reason_code="CLUSTER_REVIEW",
                title="Shared-attribute cluster",
                detail="3+ vendors share attributes; compliance review.",
                claim_paths=["company.primary_contact.phone"],
                fixed_by=FixedBy.INTERNAL,
            )
        ]
    return []


@check(id="C-DUP-06", stage="S6", version=1, mandatory=True, reads=("bank.account_number",))
async def change_velocity(ctx: Any) -> list[Finding]:
    from backend.app.persistence import repo

    existing = sstr(ctx.value("existing_vendor_id"))
    if not existing:
        return []
    prior = [c for c in repo.STORE["cases"].values() if c.get("existing_vendor_id") == existing]
    if len(prior) >= 2:
        return [
            make_finding(
                ctx,
                "C-DUP-06",
                "S6",
                1,
                outcome=Outcome.FAIL,
                severity=Severity.HARD,
                reason_code="CHANGE_VELOCITY",
                title="Repeated bank changes",
                detail="2+ bank changes in window; review.",
                claim_paths=["bank.account_number"],
                fixed_by=FixedBy.INTERNAL,
                score_tags={"BANK_ID": 0.3},
            )
        ]
    return []
