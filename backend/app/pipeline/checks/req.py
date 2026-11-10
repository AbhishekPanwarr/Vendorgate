"""S2 completeness: C-REQ-01/02/03 (metadata only; doc scan is Phase 3)."""

from typing import Any

from backend.app.core.safe_eval import safe_eval
from backend.app.domain.enums import FixedBy
from backend.app.domain.enums import Outcome
from backend.app.domain.enums import Severity
from backend.app.domain.models import Finding
from backend.app.domain.models import FixAction
from backend.app.pipeline.checks._util import make_finding
from backend.app.pipeline.checks._util import sstr
from backend.app.pipeline.registry import check
from backend.app.risk.tiers import provisional_tier


def _eval_ctx(ctx: Any) -> dict[str, object]:
    raw = {
        "bank.country": str(ctx.value("bank.country")),
        "company.country": str(ctx.value("company.country")),
        "category": str(ctx.value("requester.category")),
        "entity_type": str(ctx.value("company.entity_type")),
        "tax.form_type": str(ctx.value("tax.form_type")),
        "provisional_tier": _prov(ctx),
        "true": True,
    }
    # safe_eval allows only bare Names: map dotted paths to identifiers
    return {k.replace(".", "__"): v for k, v in raw.items()}


def _expr(expr: str) -> str:
    for dotted in ("bank.country", "company.country", "tax.form_type"):
        expr = expr.replace(dotted, dotted.replace(".", "__"))
    return expr


def _prov(ctx: Any) -> str:  # noqa: ANN401
    usd = float(ctx.value("requester.expected_annual_spend_usd") or 0)
    return provisional_tier(
        usd,
        str(ctx.value("requester.category")),
        str(ctx.value("company.country")),
        ctx.policy,
    )


def _active(items: list[dict[str, object]], ectx: dict[str, object]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for it in items:
        if safe_eval(_expr(str(it.get("when", "true"))), ectx):
            out.append(it)
    return out


@check(id="C-REQ-01", stage="S2", version=1, mandatory=True, reads=("tax.tax_id",))
async def req_fields(ctx: Any) -> list[Finding]:
    req = ctx.policy.requirements(
        str(ctx.value("company.country")),
        str(ctx.value("company.entity_type")),
        str(ctx.value("requester.category")),
        _prov(ctx),
        "NEW_VENDOR",
    )
    ectx = _eval_ctx(ctx)
    findings: list[Finding] = []
    fields = req.get("fields", []) if isinstance(req, dict) else []
    for item in _active(fields, ectx):
        path = sstr(item["path"])
        if ctx.value(path) in (None, ""):
            findings.append(
                make_finding(
                    ctx,
                    "C-REQ-01",
                    "S2",
                    1,
                    outcome=Outcome.FAIL,
                    severity=Severity.SOFT,
                    reason_code="MISSING_FIELD",
                    title=f"Missing field {path}",
                    detail=f"Required field {path} is missing.",
                    claim_paths=[path],
                    fix=FixAction(code=sstr(item.get("fix", "PROVIDE_FIELD")), field_paths=[path]),
                    fixed_by=FixedBy.VENDOR,
                    score_tags={"DOCS": 0.1},
                    subject=path,
                )
            )
    conds = req.get("conditional", []) if isinstance(req, dict) else []
    for item in _active(conds, ectx):
        path = sstr(item["path"])
        if ctx.value(path) in (None, ""):
            findings.append(
                make_finding(
                    ctx,
                    "C-REQ-03",
                    "S2",
                    1,
                    outcome=Outcome.FAIL,
                    severity=Severity.SOFT,
                    reason_code="MISSING_CONDITIONAL",
                    title=f"Missing conditional {path}",
                    detail=f"Conditional item {path} is required.",
                    claim_paths=[path],
                    fix=FixAction(code="PROVIDE_JUSTIFICATION", field_paths=[path]),
                    fixed_by=FixedBy.VENDOR,
                    score_tags={"DOCS": 0.1},
                    subject=path,
                )
            )
    return findings


@check(id="C-REQ-02", stage="S2", version=1, mandatory=True, reads=("documents.0.doc_type",))
async def req_docs(ctx: Any) -> list[Finding]:
    req = ctx.policy.requirements(
        str(ctx.value("company.country")),
        str(ctx.value("company.entity_type")),
        str(ctx.value("requester.category")),
        _prov(ctx),
        "NEW_VENDOR",
    )
    ectx = _eval_ctx(ctx)
    present = set()
    i = 0
    while True:
        v = ctx.value(f"documents.{i}.doc_type")
        if v is None:
            break
        present.add(str(v))
        i += 1
    findings: list[Finding] = []
    docs = req.get("docs", []) if isinstance(req, dict) else []
    for item in _active(docs, ectx):
        any_of = item.get("any_of")
        if isinstance(any_of, list):
            opts = [str(d) for d in any_of]
            if not any(d in present for d in opts):
                findings.append(
                    make_finding(
                        ctx,
                        "C-REQ-02",
                        "S2",
                        1,
                        outcome=Outcome.FAIL,
                        severity=Severity.SOFT,
                        reason_code="MISSING_DOC",
                        title=f"Missing one of {opts}",
                        detail="Upload one of the accepted bank-proof documents.",
                        fix=FixAction(code=sstr(item.get("fix", "UPLOAD_BANK_PROOF"))),
                        fixed_by=FixedBy.VENDOR,
                        score_tags={"DOCS": 0.3},
                        subject=",".join(opts),
                    )
                )
        else:
            want = sstr(item.get("doc_type"))
            if want not in present:
                findings.append(
                    make_finding(
                        ctx,
                        "C-REQ-02",
                        "S2",
                        1,
                        outcome=Outcome.FAIL,
                        severity=Severity.SOFT,
                        reason_code="MISSING_DOC",
                        title=f"Missing document {want}",
                        detail=f"Required document {want} is missing.",
                        fix=FixAction(code=sstr(item.get("fix", "UPLOAD_DOC"))),
                        fixed_by=FixedBy.VENDOR,
                        score_tags={"DOCS": 0.5},
                        subject=want,
                    )
                )
    return findings
