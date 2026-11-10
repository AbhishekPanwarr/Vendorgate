"""S4 external verification: C-VER-01..05 (mock adapters, fail-closed)."""

from typing import Any

from backend.app.adapters.base import AdapterUnavailable
from backend.app.adapters.base import VerifierStatus
from backend.app.adapters.mocks.verifiers import BankMock
from backend.app.adapters.mocks.verifiers import GstMock
from backend.app.adapters.mocks.verifiers import IrsMock
from backend.app.adapters.mocks.verifiers import RegistryMock
from backend.app.adapters.mocks.verifiers import ViesMock
from backend.app.domain.enums import FixedBy
from backend.app.domain.enums import Outcome
from backend.app.domain.enums import Severity
from backend.app.domain.models import Evidence
from backend.app.domain.models import Finding
from backend.app.domain.models import FixAction
from backend.app.pipeline.checks._util import make_finding
from backend.app.pipeline.checks._util import sstr
from backend.app.pipeline.registry import check


def _unverifiable(check_id: str, detail: str) -> Finding:
    return Finding(
        check_id=check_id,
        stage="S4",
        check_version=1,
        outcome=Outcome.UNVERIFIABLE,
        severity=Severity.HARD,
        reason_code="VERIFIER_UNAVAILABLE",
        title=f"{check_id} unverifiable",
        detail=detail,
        evidence=[Evidence(kind="adapter", ref=check_id, summary=detail)],
        fixed_by=FixedBy.INTERNAL,
        mandatory=True,
        deterministic=True,
        reads=[],
    )


def _pass(check_id: str, title: str, ref: str, call_id: str) -> Finding:
    return Finding(
        check_id=check_id,
        stage="S4",
        check_version=1,
        outcome=Outcome.PASS,
        severity=Severity.INFO,
        title=title,
        detail=title,
        evidence=[Evidence(kind="adapter", ref=ref, summary=f"{ref} call {call_id}")],
        deterministic=True,
        reads=[],
    )


@check(
    id="C-VER-01",
    stage="S4",
    version=1,
    mandatory=True,
    reads=("tax.tax_id", "tax.country"),
    adapters=("irs",),
)
async def tin_match(ctx: Any) -> list[Finding]:
    if sstr(ctx.value("tax.country")) != "US":
        return []
    tax_id = sstr(ctx.value("tax.tax_id"))
    try:
        res = await IrsMock().verify({"tax_id": tax_id}, timeout=5.0)
    except AdapterUnavailable as e:
        return [_unverifiable("C-VER-01", str(e))]
    if res.status == VerifierStatus.NOT_FOUND:
        return [
            make_finding(
                ctx,
                "C-VER-01",
                "S4",
                1,
                outcome=Outcome.FAIL,
                severity=Severity.SOFT,
                reason_code="TIN_NAME_MISMATCH",
                title="TIN not on file",
                detail="No IRS record for this TIN.",
                claim_paths=["tax.tax_id"],
                fix=FixAction(code="PROVIDE_TIN", field_paths=["tax.tax_id"]),
                fixed_by=FixedBy.VENDOR,
            )
        ]
    code = (res.data or {}).get("code")
    if code in (0, 6, 7, 8):
        return [_pass("C-VER-01", "TIN match", "irs", res.call_id)]
    if code == 1:
        return [
            make_finding(
                ctx,
                "C-VER-01",
                "S4",
                1,
                outcome=Outcome.FAIL,
                severity=Severity.SOFT,
                reason_code="TIN_MISSING_OR_MALFORMED",
                title="TIN missing or malformed",
                detail="IRS code 1.",
                claim_paths=["tax.tax_id"],
                fix=FixAction(code="PROVIDE_TIN", field_paths=["tax.tax_id"]),
                fixed_by=FixedBy.VENDOR,
            )
        ]
    if code == 2:
        return [
            make_finding(
                ctx,
                "C-VER-01",
                "S4",
                1,
                outcome=Outcome.FAIL,
                severity=Severity.HARD,
                reason_code="TIN_NOT_ISSUED",
                title="TIN not issued",
                detail="IRS has not issued this TIN; supply IRS confirmation letter.",
                claim_paths=["tax.tax_id"],
                fix=FixAction(code="PROVIDE_TIN_LETTER", field_paths=["tax.tax_id"]),
                fixed_by=FixedBy.VENDOR,
                score_tags={"BANK_ID": 0.6},
            )
        ]
    if code == 3:
        return [
            make_finding(
                ctx,
                "C-VER-01",
                "S4",
                1,
                outcome=Outcome.FAIL,
                severity=Severity.SOFT,
                reason_code="TIN_NAME_MISMATCH",
                title="TIN name mismatch",
                detail="Name and TIN do not match IRS records; use exact legal name.",
                claim_paths=["tax.tax_id", "company.legal_name"],
                fix=FixAction(code="CONFIRM_TIN_NAME", field_paths=["company.legal_name"]),
                fixed_by=FixedBy.VENDOR,
                score_tags={"BANK_ID": 0.2},
            )
        ]
    return [_unverifiable("C-VER-01", f"unexpected IRS code {code}")]


@check(
    id="C-VER-02",
    stage="S4",
    version=1,
    mandatory=True,
    reads=("tax.tax_id", "tax.country"),
    adapters=("gst",),
)
async def gst_registry(ctx: Any) -> list[Finding]:
    if sstr(ctx.value("tax.country")) != "IN":
        return []
    gstin = sstr(ctx.value("tax.tax_id"))
    try:
        res = await GstMock().verify({"gstin": gstin}, timeout=5.0)
    except AdapterUnavailable as e:
        return [_unverifiable("C-VER-02", str(e))]
    if res.status == VerifierStatus.NOT_FOUND:
        return [
            make_finding(
                ctx,
                "C-VER-02",
                "S4",
                1,
                outcome=Outcome.FAIL,
                severity=Severity.HARD,
                reason_code="GSTIN_NOT_FOUND",
                title="GSTIN not found",
                detail="No GST registry record.",
                claim_paths=["tax.tax_id"],
                fix=FixAction(code="PROVIDE_GSTIN", field_paths=["tax.tax_id"]),
                fixed_by=FixedBy.VENDOR,
            )
        ]
    state = (res.data or {}).get("state")
    if state == "Active":
        return [_pass("C-VER-02", "GSTIN active", "gst", res.call_id)]
    return [
        make_finding(
            ctx,
            "C-VER-02",
            "S4",
            1,
            outcome=Outcome.FAIL,
            severity=Severity.HARD,
            reason_code="GSTIN_NOT_ACTIVE",
            title=f"GSTIN {state}",
            detail="GSTIN is not active.",
            claim_paths=["tax.tax_id"],
            fixed_by=FixedBy.NONE,
        )
    ]


@check(
    id="C-VER-03",
    stage="S4",
    version=1,
    mandatory=True,
    reads=("tax.tax_id", "tax.country"),
    adapters=("vies",),
)
async def vies_check(ctx: Any) -> list[Finding]:
    country = sstr(ctx.value("tax.country"))
    if country not in ("GB", "DE"):
        return []
    vat_id = sstr(ctx.value("tax.tax_id"))
    try:
        res = await ViesMock().verify({"vat_id": vat_id}, timeout=5.0)
    except AdapterUnavailable as e:
        return [_unverifiable("C-VER-03", str(e))]
    if res.status == VerifierStatus.NOT_FOUND or not (res.data or {}).get("valid"):
        return [
            make_finding(
                ctx,
                "C-VER-03",
                "S4",
                1,
                outcome=Outcome.FAIL,
                severity=Severity.HARD,
                reason_code="VAT_INVALID",
                title="VAT ID invalid",
                detail="VIES reports invalid.",
                claim_paths=["tax.tax_id"],
                fix=FixAction(code="PROVIDE_VAT", field_paths=["tax.tax_id"]),
                fixed_by=FixedBy.VENDOR,
            )
        ]
    return [_pass("C-VER-03", "VAT valid", "vies", res.call_id)]


@check(
    id="C-VER-04",
    stage="S4",
    version=1,
    mandatory=True,
    reads=("company.legal_name", "company.country", "company.entity_type"),
    adapters=("registry",),
)
async def registry_check(ctx: Any) -> list[Finding]:
    from backend.app.risk.tiers import provisional_tier

    entity = sstr(ctx.value("company.entity_type"))
    if "SOLE" in entity.upper():
        return []
    usd = float(ctx.value("requester.expected_annual_spend_usd") or 0)
    tier = provisional_tier(
        usd, sstr(ctx.value("requester.category")), sstr(ctx.value("company.country")), ctx.policy
    )
    if tier == "LOW":
        return []  # tier-excluded; not registered-to-run at LOW (logged in decisions.md)
    legal = sstr(ctx.value("company.legal_name"))
    from backend.app.matching.normalize import canon_text

    key, _ = canon_text(legal)
    try:
        res = await RegistryMock().verify({"name_key": key}, timeout=5.0)
    except AdapterUnavailable as e:
        return [_unverifiable("C-VER-04", str(e))]
    if res.status == VerifierStatus.NOT_FOUND:
        return [
            make_finding(
                ctx,
                "C-VER-04",
                "S4",
                1,
                outcome=Outcome.FAIL,
                severity=Severity.SOFT,
                reason_code="UPLOAD_INCORP_CERT",
                title="Entity not found in registry",
                detail="Upload certificate of incorporation.",
                claim_paths=["company.legal_name"],
                fix=FixAction(code="UPLOAD_INCORP_CERT", field_paths=["company.legal_name"]),
                fixed_by=FixedBy.VENDOR,
            )
        ]
    status = (res.data or {}).get("status")
    if status == "Active":
        return [_pass("C-VER-04", "Entity active", "registry", res.call_id)]
    if status in ("Dissolved", "StruckOff"):
        return [
            make_finding(
                ctx,
                "C-VER-04",
                "S4",
                1,
                outcome=Outcome.FAIL,
                severity=Severity.HARD,
                reason_code="ENTITY_NOT_ACTIVE",
                title=f"Entity {status}",
                detail="Registry reports inactive.",
                claim_paths=["company.legal_name"],
                fixed_by=FixedBy.NONE,
            )
        ]
    return [
        make_finding(
            ctx,
            "C-VER-04",
            "S4",
            1,
            outcome=Outcome.FAIL,
            severity=Severity.HARD,
            reason_code="LIQUIDATION_REVIEW",
            title=f"Entity {status}",
            detail="Requires controller review.",
            claim_paths=["company.legal_name"],
            fixed_by=FixedBy.INTERNAL,
        )
    ]


@check(
    id="C-VER-05",
    stage="S4",
    version=1,
    mandatory=True,
    reads=("bank.account_number", "bank.country", "bank.routing_number", "bank.ifsc", "bank.iban"),
    adapters=("bank",),
)
async def bank_ownership(ctx: Any) -> list[Finding]:
    country = sstr(ctx.value("bank.country"))
    acct = "".join(ch for ch in sstr(ctx.value("bank.account_number")) if ch.isdigit())
    if country == "US":
        key = f"US|{sstr(ctx.value('bank.routing_number'))}|{acct}"
    elif country == "IN":
        key = f"IN|{sstr(ctx.value('bank.ifsc'))}|{acct}"
    else:
        key = f"{country}|{sstr(ctx.value('bank.swift_bic'))}|{acct}"
    try:
        res = await BankMock().verify({"acct_key": key}, timeout=5.0)
    except AdapterUnavailable as e:
        return [_unverifiable("C-VER-05", str(e))]
    if res.status == VerifierStatus.NOT_FOUND:
        return [
            make_finding(
                ctx,
                "C-VER-05",
                "S4",
                1,
                outcome=Outcome.FAIL,
                severity=Severity.SOFT,
                reason_code="BANK_ACCOUNT_NOT_FOUND",
                title="Bank account not found",
                detail="Ownership validation found no such account.",
                claim_paths=["bank.account_number"],
                fix=FixAction(code="PROVIDE_BANK_PROOF", field_paths=["bank.account_number"]),
                fixed_by=FixedBy.VENDOR,
                score_tags={"BANK_ID": 0.5},
            )
        ]
    return [_pass("C-VER-05", "Bank ownership verified", "bank", res.call_id)]
