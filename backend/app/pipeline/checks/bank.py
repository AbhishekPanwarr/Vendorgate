"""S3 bank + contact checks C-BNK-01..03, C-CON-01."""

import re

from backend.app.domain.enums import FixedBy
from backend.app.domain.enums import Outcome
from backend.app.domain.enums import Severity
from backend.app.domain.models import Finding
from backend.app.domain.models import FixAction
from backend.app.pipeline.checks._util import make_finding
from backend.app.pipeline.registry import check
from backend.app.validators.ein import validate_aba
from backend.app.validators.gstin import validate_ifsc
from backend.app.validators.iban import validate_iban
from backend.app.validators.iban import validate_swift
from backend.app.validators.phone import validate_phone


def _fail(
    ctx: object,
    check_id: str,
    code: str,
    title: str,
    paths: list[str],
    fix_code: str = "PROVIDE_BANK_DETAILS",
) -> Finding:
    return make_finding(
        ctx,
        check_id,
        "S3",
        1,
        outcome=Outcome.FAIL,
        severity=Severity.SOFT,
        reason_code=code,
        title=title,
        detail=title,
        claim_paths=paths,
        fix=FixAction(code=fix_code, field_paths=paths),
        fixed_by=FixedBy.VENDOR,
    )


def _val(ctx: object, path: str) -> str:
    return str(ctx.value(path) or "")  # type: ignore[attr-defined]


@check(
    id="C-BNK-01",
    stage="S3",
    version=1,
    mandatory=True,
    reads=(
        "bank.routing_number",
        "bank.ifsc",
        "bank.iban",
        "bank.sort_code",
        "bank.account_number",
        "bank.country",
    ),
)
async def bank_format(ctx: object) -> list[Finding]:
    country = _val(ctx, "bank.country")
    findings: list[Finding] = []
    if country == "US":
        if not re.fullmatch(r"\d{9}", _val(ctx, "bank.routing_number")):
            findings.append(
                _fail(
                    ctx,
                    "C-BNK-01",
                    "BANK_FORMAT_INVALID",
                    "Routing number must be 9 digits.",
                    ["bank.routing_number"],
                )
            )
        if not 4 <= len(_val(ctx, "bank.account_number")) <= 17:
            findings.append(
                _fail(
                    ctx,
                    "C-BNK-01",
                    "BANK_FORMAT_INVALID",
                    "Account number must be 4-17 digits.",
                    ["bank.account_number"],
                )
            )
    elif country == "IN":
        raw_ifsc = _val(ctx, "bank.ifsc")
        if not validate_ifsc(raw_ifsc).valid:
            findings.append(
                _fail(
                    ctx,
                    "C-BNK-01",
                    "BANK_FORMAT_INVALID",
                    f"IFSC {raw_ifsc!r} has bad format.",
                    ["bank.ifsc"],
                )
            )
    else:
        raw_iban = _val(ctx, "bank.iban")
        if raw_iban:
            res = validate_iban(raw_iban)
            if not res.valid and res.reason in ("BAD_LENGTH", "BAD_STRUCTURE", "BAD_CHARSET"):
                findings.append(
                    _fail(
                        ctx,
                        "C-BNK-01",
                        "BANK_FORMAT_INVALID",
                        f"IBAN: {res.reason}.",
                        ["bank.iban"],
                    )
                )
    return findings


@check(
    id="C-BNK-02",
    stage="S3",
    version=1,
    mandatory=True,
    reads=("bank.routing_number", "bank.ifsc", "bank.iban", "bank.country"),
)
async def bank_checksum(ctx: object) -> list[Finding]:
    country = _val(ctx, "bank.country")
    if country == "US":
        raw_routing = _val(ctx, "bank.routing_number")
        if re.fullmatch(r"\d{9}", raw_routing) and not validate_aba(raw_routing).valid:
            return [
                _fail(
                    ctx,
                    "C-BNK-02",
                    "BANK_CHECKSUM_INVALID",
                    "Routing number checksum invalid.",
                    ["bank.routing_number"],
                )
            ]
    elif country not in ("IN", "US"):
        raw_iban = _val(ctx, "bank.iban")
        if raw_iban:
            res = validate_iban(raw_iban)
            if not res.valid and res.reason == "BAD_CHECKSUM":
                return [
                    _fail(
                        ctx,
                        "C-BNK-02",
                        "BANK_CHECKSUM_INVALID",
                        "IBAN checksum invalid.",
                        ["bank.iban"],
                    )
                ]
    return []


@check(
    id="C-BNK-03",
    stage="S3",
    version=1,
    mandatory=True,
    reads=("bank.iban", "bank.swift_bic", "bank.country", "bank.currency"),
)
async def bank_coherence(ctx: object) -> list[Finding]:
    raw_iban = _val(ctx, "bank.iban")
    raw_swift = _val(ctx, "bank.swift_bic")
    if raw_iban and raw_swift:
        res = validate_swift(raw_swift)
        if res.valid and res.details.get("country") != raw_iban[:2]:
            return [
                _fail(
                    ctx,
                    "C-BNK-03",
                    "BANK_COUNTRY_INCOHERENT",
                    "SWIFT country differs from IBAN country.",
                    ["bank.iban", "bank.swift_bic"],
                )
            ]
    return []


@check(
    id="C-CON-01",
    stage="S3",
    version=1,
    mandatory=True,
    reads=(
        "company.primary_contact.email",
        "company.ap_contact.email",
        "company.primary_contact.phone",
        "company.country",
    ),
)
async def contact_format(ctx: object) -> list[Finding]:
    findings: list[Finding] = []
    country = _val(ctx, "company.country")
    for role in ("company.primary_contact.email", "company.ap_contact.email"):
        email = _val(ctx, role)
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            findings.append(
                _fail(
                    ctx,
                    "C-CON-01",
                    "CONTACT_INVALID",
                    f"Email {email!r} is invalid.",
                    [role],
                    fix_code="PROVIDE_CONTACT",
                )
            )
    phone = _val(ctx, "company.primary_contact.phone")
    if not validate_phone(phone, country).valid:
        findings.append(
            _fail(
                ctx,
                "C-CON-01",
                "CONTACT_INVALID",
                f"Phone {phone!r} is invalid for {country}.",
                ["company.primary_contact.phone"],
                fix_code="PROVIDE_CONTACT",
            )
        )
    return findings
