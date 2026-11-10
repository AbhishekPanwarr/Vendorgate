"""S5 name checks (Phase 1: C-NAME-02 only; 01/03/04 need S1/S4)."""

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
async def name_bank(ctx: object) -> list[Finding]:
    legal = str(ctx.value("company.legal_name") or "")  # type: ignore[attr-defined]
    holder = str(ctx.value("bank.account_holder_name") or "")  # type: ignore[attr-defined]
    cfg = ctx.policy.raw["base"]["matching"]["name"]  # type: ignore[attr-defined]
    comp = compare_names(parse_name(legal), parse_name(holder), dict(cfg))
    paths = ["company.legal_name", "bank.account_holder_name"]
    if comp.relation in ("EXACT", "EQUIVALENT"):
        return []
    if comp.relation == "FORM_CONFLICT":
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
    entity = str(ctx.value("company.entity_type") or "").upper()  # type: ignore[attr-defined]
    if comp.relation == "DIFFERENT" and "SOLE" in entity:
        owner = str(ctx.value("company.owners.0.name") or "")  # type: ignore[attr-defined]
        if owner:
            oc = compare_names(parse_name(owner), parse_name(holder), dict(cfg))
            if oc.relation in ("EXACT", "EQUIVALENT"):
                return []  # sole prop: holder is the declared owner (M-14 control)
    sev = Severity.HARD if comp.relation == "DIFFERENT" else Severity.SOFT
    code = "NAME_MISMATCH_BANK" if comp.relation == "DIFFERENT" else "NAME_UNCONFIRMED"
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
