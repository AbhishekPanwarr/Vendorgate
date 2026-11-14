"""S5 name checks (Phase 1: C-NAME-02 only; 01/03/04 need S1/S4)."""

from typing import Any

from backend.app.domain.enums import FixedBy
from backend.app.domain.enums import Outcome
from backend.app.domain.enums import Severity
from backend.app.domain.models import Finding
from backend.app.domain.models import FixAction
from backend.app.matching.name_compare import compare_names
from backend.app.matching.name_compare import parse_name
from backend.app.pipeline.checks._util import make_finding
from backend.app.pipeline.registry import check


@check(
    id="C-NAME-02",
    stage="S5",
    version=1,
    mandatory=True,
    reads=(
        "company.legal_name",
        "bank.account_holder_name",
        "company.entity_type",
        "company.owners.0.name",
    ),
)
async def name_bank(ctx: Any) -> list[Finding]:
    legal = str(ctx.value("company.legal_name") or "")
    holder = str(ctx.value("bank.account_holder_name") or "")
    cfg = ctx.policy.raw["base"]["matching"]["name"]
    comp = compare_names(parse_name(legal), parse_name(holder), dict(cfg))
    paths = ["company.legal_name", "bank.account_holder_name"]
    if comp.relation in ("EXACT", "EQUIVALENT"):
        return []
    if comp.relation == "FORM_CONFLICT":
        _enqueue(
            ctx,
            "C-NAME-02",
            legal,
            holder,
            _k3_corrobators(ctx, holder),
            {"core_similarity": comp.core_sim, "legal_form_relation": comp.form_rel},
        )
        return [
            make_finding(
                ctx,
                "C-NAME-02",
                "S5",
                1,
                outcome=Outcome.FAIL,
                severity=Severity.SOFT,
                reason_code="LEGAL_FORM_UNCONFIRMED",
                title="Name ↔ bank holder: legal form unconfirmed",
                detail=f"Form says {legal!r}, bank account is held by {holder!r}. "
                "They look like the same business but the legal form is unconfirmed.",
                claim_paths=paths,
                fix=FixAction(code="UPLOAD_DBA_PROOF", field_paths=paths),
                fixed_by=FixedBy.VENDOR,
                score_tags={"BANK_ID": 0.5},
            )
        ]
    # CORE_FUZZY without corroborator (none in Phase 1) or DIFFERENT
    entity = str(ctx.value("company.entity_type") or "").upper()
    if comp.relation == "DIFFERENT" and "SOLE" in entity:
        owner = str(ctx.value("company.owners.0.name") or "")
        if owner:
            oc = compare_names(parse_name(owner), parse_name(holder), dict(cfg))
            if oc.relation in ("EXACT", "EQUIVALENT"):
                return []  # sole prop: holder is the declared owner (M-14 control)
    sev = Severity.HARD if comp.relation == "DIFFERENT" else Severity.SOFT
    code = "NAME_MISMATCH_BANK" if comp.relation == "DIFFERENT" else "NAME_UNCONFIRMED"
    if comp.relation == "CORE_FUZZY":
        _enqueue(
            ctx,
            "C-NAME-02",
            legal,
            holder,
            _k3_corrobators(ctx, holder),
            {"core_similarity": comp.core_sim, "legal_form_relation": comp.form_rel},
        )
    return [
        make_finding(
            ctx,
            "C-NAME-02",
            "S5",
            1,
            outcome=Outcome.FAIL,
            severity=sev,
            reason_code=code,
            title="Name ↔ bank holder mismatch",
            detail=f"Form says {legal!r}, bank account is held by {holder!r}.",
            claim_paths=paths,
            fix=FixAction(code="CONFIRM_BANK_HOLDER", field_paths=paths),
            fixed_by=FixedBy.VENDOR,
            score_tags={"BANK_ID": 0.5},
        )
    ]


@check(
    id="C-NAME-03",
    stage="S5",
    version=2,
    mandatory=True,
    reads=(
        "company.legal_name",
        "company.country",
        "company.entity_type",
        "requester.expected_annual_spend_usd",
        "requester.category",
    ),
)
async def name_registry(ctx: Any) -> list[Finding]:
    from backend.app.adapters.mocks.verifiers import RegistryMock
    from backend.app.matching.normalize import canon_text
    from backend.app.risk.tiers import provisional_tier

    entity = str(ctx.value("company.entity_type") or "")
    if "SOLE" in entity.upper():
        return []
    usd = float(ctx.value("requester.expected_annual_spend_usd") or 0)
    tier = provisional_tier(
        usd, str(ctx.value("requester.category")), str(ctx.value("company.country")), ctx.policy
    )
    if tier == "LOW":
        return []
    legal = str(ctx.value("company.legal_name") or "")
    key, _ = canon_text(legal)
    try:
        res = await RegistryMock().verify({"name_key": key}, timeout=5.0)
    except Exception:
        return []
    if res.status.value == "NOT_FOUND":
        return []
    reg_name = str((res.data or {}).get("legal_name", ""))
    if not reg_name:
        return []
    cfg = dict(ctx.policy.raw["base"]["matching"]["name"])
    comp = compare_names(parse_name(legal), parse_name(reg_name), cfg)
    if comp.relation in ("EXACT", "EQUIVALENT"):
        return []
    return [
        make_finding(
            ctx,
            "C-NAME-03",
            "S5",
            1,
            outcome=Outcome.FAIL,
            severity=Severity.SOFT,
            reason_code="NAME_UNCONFIRMED",
            title="Name differs from registry record",
            detail=f"Form says {legal!r}, registry says {reg_name!r}.",
            claim_paths=["company.legal_name"],
            fix=FixAction(code="UPLOAD_INCORP_CERT", field_paths=["company.legal_name"]),
            fixed_by=FixedBy.VENDOR,
        )
    ]


@check(
    id="C-NAME-04",
    stage="S5",
    version=1,
    mandatory=True,
    reads=("company.legal_name", "tax.tax_id", "tax.country"),
)
async def name_tax_record(ctx: Any) -> list[Finding]:
    from backend.app.adapters.mocks.verifiers import GstMock
    from backend.app.adapters.mocks.verifiers import IrsMock
    from backend.app.adapters.mocks.verifiers import ViesMock

    country = str(ctx.value("tax.country") or "")
    tax_id = str(ctx.value("tax.tax_id") or "")
    legal = str(ctx.value("company.legal_name") or "")
    try:
        if country == "US":
            res = await IrsMock().verify({"tax_id": tax_id}, timeout=5.0)
        elif country == "IN":
            res = await GstMock().verify({"gstin": tax_id}, timeout=5.0)
        else:
            res = await ViesMock().verify({"vat_id": tax_id}, timeout=5.0)
    except Exception:
        return []
    if res.status.value != "OK":
        return []
    rec_name = str((res.data or {}).get("name") or (res.data or {}).get("legal_name") or "")
    if not rec_name:
        return []
    cfg = dict(ctx.policy.raw["base"]["matching"]["name"])
    comp = compare_names(parse_name(legal), parse_name(rec_name), cfg)
    if comp.relation in ("EXACT", "EQUIVALENT"):
        return []
    return [
        make_finding(
            ctx,
            "C-NAME-04",
            "S5",
            1,
            outcome=Outcome.FAIL,
            severity=Severity.SOFT,
            reason_code="TIN_NAME_MISMATCH",
            title="Name differs from tax record",
            detail=f"Form says {legal!r}, tax record says {rec_name!r}.",
            claim_paths=["company.legal_name", "tax.tax_id"],
            fix=FixAction(code="CONFIRM_TIN_NAME", field_paths=["company.legal_name"]),
            fixed_by=FixedBy.VENDOR,
            score_tags={"BANK_ID": 0.2},
        )
    ]


@check(
    id="C-POL-02", stage="S10", version=1, mandatory=True, reads=("bank.country", "company.country")
)
async def callback_required(ctx: Any) -> list[Finding]:
    bank = str(ctx.value("bank.country") or "")
    company = str(ctx.value("company.country") or "")
    has_dup5 = any(f.check_id == "C-DUP-05" and str(f.outcome) == "FAIL" for f in ctx.findings)
    if has_dup5 or (bank and company and bank != company):
        return [
            make_finding(
                ctx,
                "C-POL-02",
                "S10",
                1,
                outcome=Outcome.FAIL,
                severity=Severity.HARD,
                reason_code="CALLBACK_REQUIRED",
                title="Independent callback required",
                detail="Policy requires an independent callback before approval.",
                claim_paths=["bank.country"],
                fix=FixAction(code="RECORD_CALLBACK", field_paths=["bank.country"]),
                fixed_by=FixedBy.INTERNAL,
            )
        ]
    return []


@check(
    id="C-NAME-01",
    stage="S5",
    version=1,
    mandatory=True,
    reads=("company.legal_name", "docs.content_hash"),
)
async def name_taxdoc(ctx: Any) -> list[Finding]:
    legal = str(ctx.value("company.legal_name") or "")
    docs = [
        c
        for p, c in ctx.claims.items()
        if p.startswith("doc:") and p.endswith(("business_name", ".name"))
    ]
    if not docs:
        return []
    cfg = dict(ctx.policy.raw["base"]["matching"]["name"])
    out = []
    for claim in docs:
        comp = compare_names(parse_name(legal), parse_name(str(claim.value or "")), cfg)
        if comp.relation in ("EXACT", "EQUIVALENT"):
            continue
        out.append(
            make_finding(
                ctx,
                "C-NAME-01",
                "S5",
                1,
                outcome=Outcome.FAIL,
                severity=Severity.SOFT,
                reason_code="NAME_UNCONFIRMED",
                title="Name differs from tax document",
                detail=f"Form says {legal!r}, tax doc says {claim.value!r}.",
                claim_paths=["company.legal_name", claim.path],
                fix=FixAction(code="CONFIRM_LEGAL_NAME", field_paths=["company.legal_name"]),
                fixed_by=FixedBy.VENDOR,
            )
        )
    return out


def _k3_corrobators(ctx: Any, variant: str) -> list[dict[str, str]]:
    """K3: official registration doc whose grounded legal name ~= variant."""
    from backend.app.matching.name_compare import compare_names as _cmp
    from backend.app.matching.name_compare import parse_name as _parse

    cfg = dict(ctx.policy.raw["base"]["matching"]["name"])
    out = []
    for path, claim in ctx.claims.items():
        if not path.startswith("doc:"):
            continue
        if path.split(".")[-1] not in ("legal_name", "business_name"):
            continue
        if not claim.value:
            continue
        if _cmp(_parse(variant), _parse(str(claim.value)), cfg).relation in ("EXACT", "EQUIVALENT"):
            out.append({"name": "K3", "summary": f"{path} names {claim.value!r}"})
    return out


def _enqueue(
    ctx: Any, check_id: str, a: str, b: str, corrs: list[dict[str, str]], det: dict[str, object]
) -> None:
    ctx.adjudications.append(
        {
            "check_id": check_id,
            "a": a,
            "source_a": "form",
            "b": b,
            "source_b": "bank",
            "country": str(ctx.value("company.country") or ""),
            "subject": None,
            "corroborators": corrs,
            "deterministic": det,
        }
    )
