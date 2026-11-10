"""C-DOC-* checks (S1). Operate on ctx.doc_reports produced by S1 ingest."""

from typing import Any

from backend.app.domain.enums import FixedBy
from backend.app.domain.enums import Outcome
from backend.app.domain.enums import Severity
from backend.app.domain.models import Finding
from backend.app.domain.models import FixAction
from backend.app.ingest import freshness as fresh
from backend.app.pipeline.checks._util import make_finding
from backend.app.pipeline.registry import check


def _reports(ctx: Any) -> list[dict[str, Any]]:
    return list(getattr(ctx, "doc_reports", {}).values())


def _fail(
    check_id: str,
    ctx: Any,
    code: str,
    title: str,
    detail: str,
    doc_id: str,
    sev: Severity = Severity.SOFT,
    fix_code: str = "",
    tags: dict[str, float] | None = None,
) -> Finding:
    return make_finding(
        ctx,
        check_id,
        "S1",
        1,
        outcome=Outcome.FAIL,
        severity=sev,
        reason_code=code,
        title=title,
        detail=detail,
        claim_paths=[],
        fix=FixAction(code=fix_code or code),
        fixed_by=FixedBy.VENDOR,
        score_tags=tags or {},
        subject=f"doc:{doc_id}",
    )


@check(id="C-DOC-00", stage="S1", version=1, mandatory=True, reads=("docs.content_hash", "documents.digest", "clock.today"))
async def upload_safety(ctx: Any) -> list[Finding]:
    out = []
    for rep in _reports(ctx):
        if not rep.get("upload_ok"):
            out.append(
                _fail(
                    "C-DOC-00",
                    ctx,
                    "UPLOAD_INVALID_FILE",
                    "Invalid upload",
                    f"{rep['doc_id']}: {rep.get('upload_reason')}",
                    rep["doc_id"],
                    Severity.HARD,
                    "REUPLOAD_VALID_FILE",
                    {"DOCS": 0.3},
                )
            )
    return out


@check(id="C-DOC-03", stage="S1", version=1, mandatory=True, reads=("docs.content_hash", "documents.digest", "clock.today"))
async def doc_type(ctx: Any) -> list[Finding]:
    out = []
    for rep in _reports(ctx):
        declared, detected = rep.get("declared"), rep.get("detected_type")
        if rep.get("upload_ok") and declared and detected and declared != detected:
            # ambiguous-margin cases go to L2; hard mismatch fails here
            if rep.get("detect_confident"):
                out.append(
                    _fail(
                        "C-DOC-03",
                        ctx,
                        "DOC_WRONG_TYPE",
                        "Wrong document content",
                        f"Declared {declared}, detected {detected}.",
                        rep["doc_id"],
                        Severity.SOFT,
                        "UPLOAD_CORRECT_DOC",
                        {"DOCS": 0.5},
                    )
                )
    return out


@check(id="C-DOC-04", stage="S1", version=1, mandatory=True, reads=("docs.content_hash", "documents.digest", "clock.today"))
async def freshness(ctx: Any) -> list[Finding]:
    out = []
    today = ctx.clock.now().date()
    for rep in _reports(ctx):
        fr = rep.get("freshness", {})
        if fr.get("coi_expiry"):
            st = fresh.coi_status(fr["coi_expiry"], today)
            if st == "EXPIRED":
                out.append(
                    _fail(
                        "C-DOC-04",
                        ctx,
                        "DOC_EXPIRED",
                        "Document expired",
                        f"{rep['doc_id']} expired {fr['coi_expiry']}.",
                        rep["doc_id"],
                        Severity.SOFT,
                        "UPLOAD_COI",
                        {"DOCS": 0.5},
                    )
                )
        if fr.get("bank_letter_date"):
            if fresh.bank_letter_stale(fr["bank_letter_date"], today):
                out.append(
                    _fail(
                        "C-DOC-04",
                        ctx,
                        "DOC_STALE",
                        "Bank letter stale",
                        f"{rep['doc_id']} older than 12 months.",
                        rep["doc_id"],
                        Severity.SOFT,
                        "UPLOAD_BANK_PROOF",
                    )
                )
    return out


@check(id="C-DOC-05", stage="S1", version=1, mandatory=True, reads=("docs.content_hash", "documents.digest", "clock.today"))
async def w9_signed(ctx: Any) -> list[Finding]:
    out = []
    for rep in _reports(ctx):
        if rep.get("detected_type") == "W9" and not rep.get("freshness", {}).get("signed"):
            out.append(
                _fail(
                    "C-DOC-05",
                    ctx,
                    "DOC_UNSIGNED",
                    "W-9 unsigned",
                    f"{rep['doc_id']} has no signature/date.",
                    rep["doc_id"],
                    Severity.SOFT,
                    "UPLOAD_W9",
                    {"DOCS": 0.3},
                )
            )
    return out


@check(id="C-DOC-07", stage="S1", version=1, mandatory=True, reads=("docs.content_hash", "documents.digest", "clock.today"))
async def unreadable(ctx: Any) -> list[Finding]:
    out = []
    for rep in _reports(ctx):
        if rep.get("upload_ok") and not rep.get("text_pages"):
            out.append(
                _fail(
                    "C-DOC-07",
                    ctx,
                    "DOC_UNREADABLE",
                    "Document unreadable",
                    f"{rep['doc_id']} yielded no text.",
                    rep["doc_id"],
                    Severity.SOFT,
                    "UPLOAD_CLEARER_COPY",
                    {"DOCS": 0.1},
                )
            )
    required = {
        "W9": ["tin", "business_name"],
        "GST_CERT": ["gstin"],
        "BANK_LETTER": ["account_holder", "account_number"],
    }
    for rep in [r for r in _reports(ctx) if r.get("upload_ok")]:
        needed = required.get(rep.get("detected_type", ""), [])
        bad = [f for f in rep.get("ungrounded", []) if f in needed]
        if bad:
            out.append(
                _fail(
                    "C-DOC-07",
                    ctx,
                    "UPLOAD_CLEARER_COPY",
                    "Unreadable required fields",
                    f"{rep['doc_id']}: {', '.join(bad)} not grounded.",
                    rep["doc_id"],
                    Severity.SOFT,
                    "UPLOAD_CLEARER_COPY",
                    {"DOCS": 0.1},
                )
            )
    return out


@check(id="C-DOC-08", stage="S1", version=1, mandatory=True, reads=("docs.content_hash", "documents.digest", "clock.today"))
async def injection(ctx: Any) -> list[Finding]:
    out = []
    for rep in _reports(ctx):
        hits = rep.get("injection_hits", [])
        if hits:
            f = _fail(
                "C-DOC-08",
                ctx,
                "DOC_INJECTION_SUSPECTED",
                "Suspicious instruction-like text in document",
                f"{rep['doc_id']}: {hits[0]}",
                rep["doc_id"],
                Severity.HARD,
                "COMPLIANCE_REVIEW",
                {"DOCS": 0.3},
            )
            f.fixed_by = FixedBy.INTERNAL
            out.append(f)
    return out


@check(
    id="C-DOC-10",
    stage="S5",
    version=1,
    mandatory=True,
    reads=("tax.tax_id", "bank.account_number", "docs.content_hash", "documents.digest"),
)
async def doc_form_identifiers(ctx: Any) -> list[Finding]:
    out = []
    form_tin = "".join(ch for ch in str(ctx.value("tax.tax_id") or "") if ch.isalnum())
    form_acct = "".join(ch for ch in str(ctx.value("bank.account_number") or "") if ch.isdigit())
    for path, claim in ctx.claims.items():
        if not path.startswith("doc:") or claim.source.value != "DOC":
            continue
        field = path.split(".")[-1]
        val = "".join(ch for ch in str(claim.value or "") if ch.isalnum())
        if field in ("tin", "gstin") and val and val.upper() != form_tin.upper():
            out.append(
                make_finding(
                    ctx,
                    "C-DOC-10",
                    "S5",
                    1,
                    outcome=Outcome.FAIL,
                    severity=Severity.HARD,
                    reason_code="DOC_FORM_MISMATCH",
                    title="Document TIN differs from form",
                    detail=f"{path} has {claim.value!r}.",
                    claim_paths=[path, "tax.tax_id"],
                    fix=FixAction(code="UPLOAD_CORRECT_DOC"),
                    fixed_by=FixedBy.VENDOR,
                    score_tags={"BANK_ID": 0.3},
                )
            )
        if field in ("account_number",) and val and val != form_acct:
            out.append(
                make_finding(
                    ctx,
                    "C-DOC-10",
                    "S5",
                    1,
                    outcome=Outcome.FAIL,
                    severity=Severity.HARD,
                    reason_code="DOC_FORM_MISMATCH",
                    title="Document account differs from form",
                    detail=f"{path} has {claim.value!r}.",
                    claim_paths=[path, "bank.account_number"],
                    fix=FixAction(code="UPLOAD_CORRECT_DOC"),
                    fixed_by=FixedBy.VENDOR,
                    score_tags={"BANK_ID": 0.3},
                )
            )
    return out
