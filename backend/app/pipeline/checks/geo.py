"""S5 geo/address/identity/credibility checks (Phase 1 deterministic subset)."""

from typing import Any

from backend.app.domain.enums import FixedBy
from backend.app.domain.enums import Outcome
from backend.app.domain.enums import Severity
from backend.app.domain.models import Finding
from backend.app.domain.models import FixAction
from backend.app.matching.normalize import canon_domain
from backend.app.matching.normalize import has_mixed_script
from backend.app.pipeline.checks._util import make_finding
from backend.app.pipeline.registry import check

_FREE_MAIL = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "proton.me"}
_PO_BOX = ("po box", "p.o. box", "post box", "postbox")


@check(
    id="C-GEO-01",
    stage="S5",
    version=1,
    mandatory=True,
    reads=(
        "company.country",
        "tax.country",
        "bank.country",
        "bank.currency",
        "company.primary_contact.phone",
    ),
)
async def geo_matrix(ctx: Any) -> list[Finding]:
    company = str(ctx.value("company.country") or "")
    tax = str(ctx.value("tax.country") or "")
    bank = str(ctx.value("bank.country") or "")
    findings: list[Finding] = []
    if tax != company:
        findings.append(
            make_finding(
                ctx,
                "C-GEO-01",
                "S5",
                1,
                outcome=Outcome.FAIL,
                severity=Severity.HARD,
                reason_code="TAX_COUNTRY_MISMATCH",
                title="Tax country differs from company country",
                detail=f"Company is {company} but tax country is {tax}.",
                claim_paths=["company.country", "tax.country"],
                fix=FixAction(code="CONFIRM_TAX_COUNTRY", field_paths=["tax.country"]),
                fixed_by=FixedBy.VENDOR,
                score_tags={"GEO": 0.3},
            )
        )
    if bank != company:
        findings.append(
            make_finding(
                ctx,
                "C-GEO-01",
                "S5",
                1,
                outcome=Outcome.FAIL,
                severity=Severity.SOFT,
                reason_code="BANK_COUNTRY_MISMATCH",
                title="Bank country differs from company country",
                detail=f"Company is {company} but bank is {bank}. Justification required.",
                claim_paths=["company.country", "bank.country"],
                fix=FixAction(
                    code="PROVIDE_BANK_COUNTRY_JUSTIFICATION",
                    field_paths=["declarations.bank_change_justification"],
                ),
                fixed_by=FixedBy.VENDOR,
                score_tags={"GEO": 0.3},
            )
        )
    return findings


@check(
    id="C-GEO-02",
    stage="S5",
    version=1,
    mandatory=True,
    reads=("company.registered_address", "company.remit_to_address"),
)
async def remit_justification(ctx: Any) -> list[Finding]:
    reg = str(ctx.value("company.registered_address") or "")
    remit = ctx.value("company.remit_to_address")
    just = ctx.value("declarations.remit_address_justification")
    if remit and str(remit) != reg and not just:
        return [
            make_finding(
                ctx,
                "C-GEO-02",
                "S5",
                1,
                outcome=Outcome.FAIL,
                severity=Severity.SOFT,
                reason_code="REMIT_ADDRESS_UNJUSTIFIED",
                title="Remit-to address differs without justification",
                detail="Remit-to address differs from registered address; add justification.",
                claim_paths=["company.remit_to_address"],
                fix=FixAction(
                    code="PROVIDE_REMIT_JUSTIFICATION",
                    field_paths=["declarations.remit_address_justification"],
                ),
                fixed_by=FixedBy.VENDOR,
            )
        ]
    return []


@check(id="C-ADDR-01", stage="S5", version=1, mandatory=True, reads=("company.registered_address",))
async def po_box(ctx: Any) -> list[Finding]:
    addr = str(ctx.value("company.registered_address") or "").lower()
    if any(p in addr for p in _PO_BOX):
        return [
            make_finding(
                ctx,
                "C-ADDR-01",
                "S5",
                1,
                outcome=Outcome.FAIL,
                severity=Severity.SOFT,
                reason_code="PO_BOX_REGISTERED_ADDRESS",
                title="PO-box registered address",
                detail="Registered address is a PO box; provide a physical address.",
                claim_paths=["company.registered_address"],
                fix=FixAction(
                    code="PROVIDE_PHYSICAL_ADDRESS", field_paths=["company.registered_address"]
                ),
                fixed_by=FixedBy.VENDOR,
                score_tags={"BANK_ID": 0.2},
            )
        ]
    return []


@check(
    id="C-ID-01",
    stage="S5",
    version=1,
    mandatory=False,
    reads=("company.website", "company.primary_contact.email"),
)
async def domain_checks(ctx: Any) -> list[Finding]:
    findings: list[Finding] = []
    site = canon_domain(str(ctx.value("company.website") or ""))
    email = str(ctx.value("company.primary_contact.email") or "")
    domain = canon_domain(email)
    if site and domain and domain != site:
        findings.append(
            make_finding(
                ctx,
                "C-ID-01",
                "S5",
                1,
                outcome=Outcome.WARN,
                severity=Severity.INFO,
                reason_code="DOMAIN_MISMATCH",
                title="Email domain differs from website",
                detail=f"Email domain {domain!r} differs from website {site!r}.",
                claim_paths=["company.website", "company.primary_contact.email"],
                score_tags={"BANK_ID": 0.15},
            )
        )
    if domain in _FREE_MAIL:
        findings.append(
            make_finding(
                ctx,
                "C-ID-02",
                "S5",
                1,
                outcome=Outcome.WARN,
                severity=Severity.INFO,
                reason_code="FREE_EMAIL_ENTITY",
                title="Free-mail contact for an entity",
                detail=f"Contact uses free-mail domain {domain!r}.",
                claim_paths=["company.primary_contact.email"],
                score_tags={"BANK_ID": 0.15},
            )
        )
    legal = str(ctx.value("company.legal_name") or "")
    if any(has_mixed_script(tok) for tok in legal.split()) or has_mixed_script(domain):
        findings.append(
            make_finding(
                ctx,
                "C-ID-04",
                "S5",
                1,
                outcome=Outcome.FAIL,
                severity=Severity.SOFT,
                reason_code="HOMOGLYPH_SUSPECT",
                title="Possible homoglyph in name or domain",
                detail="A token mixes Latin with Cyrillic/Greek lookalikes.",
                claim_paths=["company.legal_name"],
                fix=FixAction(code="CONFIRM_LEGAL_NAME", field_paths=["company.legal_name"]),
                fixed_by=FixedBy.VENDOR,
                score_tags={"BANK_ID": 0.3},
            )
        )
    return findings


@check(id="C-CRD-01", stage="S5", version=1, mandatory=True, reads=("company.incorporation_date",))
async def entity_age(ctx: Any) -> list[Finding]:
    from datetime import date

    raw = str(ctx.value("company.incorporation_date") or "")
    try:
        incorp = date.fromisoformat(raw)
    except ValueError:
        return []
    now = ctx.clock.now().date()  # W-2: clock, never datetime.now()
    age_days = (now - incorp).days
    if age_days < 365:
        return [
            make_finding(
                ctx,
                "C-CRD-01",
                "S5",
                1,
                outcome=Outcome.WARN,
                severity=Severity.INFO,
                reason_code="ENTITY_TOO_NEW",
                title="Entity less than 12 months old",
                detail=f"Incorporated {raw}; heightened review for young entities.",
                claim_paths=["company.incorporation_date"],
                score_tags={"REGISTRY_MEDIA": 0.5},
            )
        ]
    if age_days < 3 * 365:
        return [
            make_finding(
                ctx,
                "C-CRD-01",
                "S5",
                1,
                outcome=Outcome.WARN,
                severity=Severity.INFO,
                reason_code="ENTITY_RECENT",
                title="Entity less than 3 years old",
                detail=f"Incorporated {raw}.",
                claim_paths=["company.incorporation_date"],
                score_tags={"REGISTRY_MEDIA": 0.2},
            )
        ]
    return []
