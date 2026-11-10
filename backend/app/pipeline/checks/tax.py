"""S3 tax checks C-TAX-01..07."""

import re

from backend.app.domain.enums import FixedBy
from backend.app.domain.enums import Outcome
from backend.app.domain.enums import Severity
from backend.app.domain.models import Finding
from backend.app.domain.models import FixAction
from backend.app.pipeline.checks._util import make_finding
from backend.app.pipeline.registry import check
from backend.app.validators.ein import validate_ein
from backend.app.validators.gstin import validate_gstin
from backend.app.validators.gstin import validate_pan
from backend.app.validators.vat import validate_vat

_EIN_SHAPE = re.compile(r"^\d{2}-?\d{7}$")


def _looks_like(value: str) -> str | None:
    v = (value or "").strip().upper()
    if _EIN_SHAPE.match(v):
        return "EIN"
    if re.match(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$", v):
        return "GSTIN"
    if re.match(r"^[A-Z]{5}\d{4}[A-Z]$", v):
        return "PAN"
    if re.match(r"^(GB|DE|FR|IT|ES|NL|IE)[A-Z0-9]{8,}$", v):
        return "VAT"
    return None


def _fail(
    ctx: object,
    check_id: str,
    code: str,
    title: str,
    detail: str,
    paths: list[str],
    severity: Severity = Severity.SOFT,
    tags: dict[str, float] | None = None,
    fix_code: str = "PROVIDE_TAX_ID",
) -> Finding:
    return make_finding(
        ctx,
        check_id,
        "S3",
        1,
        outcome=Outcome.FAIL,
        severity=severity,
        reason_code=code,
        title=title,
        detail=detail,
        claim_paths=paths,
        fix=FixAction(code=fix_code, field_paths=paths),
        fixed_by=FixedBy.VENDOR,
        score_tags=tags or {},
    )


@check(id="C-TAX-01", stage="S3", version=1, mandatory=True, reads=("tax.tax_id", "tax.country"))
async def tax_format(ctx: object) -> list[Finding]:
    country = str(ctx.value("tax.country"))  # type: ignore[attr-defined]
    tax_id = str(ctx.value("tax.tax_id") or "")  # type: ignore[attr-defined]
    findings: list[Finding] = []
    if country == "US":
        res = validate_ein(tax_id)
        if not res.valid:
            findings.append(
                _fail(
                    ctx,
                    "C-TAX-01",
                    "TAX_FORMAT_INVALID",
                    "EIN format invalid",
                    f"EIN value {tax_id!r} failed format: {res.reason}.",
                    ["tax.tax_id"],
                )
            )
    elif country == "IN":
        res = validate_gstin(tax_id)
        if not res.valid and res.reason in ("BAD_LENGTH", "BAD_STRUCTURE", "BAD_CHARSET"):
            findings.append(
                _fail(
                    ctx,
                    "C-TAX-01",
                    "TAX_FORMAT_INVALID",
                    "GSTIN format invalid",
                    f"GSTIN {tax_id!r}: {res.reason}.",
                    ["tax.tax_id"],
                )
            )
    elif country in ("GB", "DE"):
        res = validate_vat(tax_id, country)
        if not res.valid and res.reason in ("BAD_LENGTH", "BAD_STRUCTURE", "BAD_CHARSET"):
            findings.append(
                _fail(
                    ctx,
                    "C-TAX-01",
                    "TAX_FORMAT_INVALID",
                    "VAT format invalid",
                    f"VAT {tax_id!r}: {res.reason}.",
                    ["tax.tax_id"],
                )
            )
    return findings


@check(id="C-TAX-02", stage="S3", version=1, mandatory=True, reads=("tax.tax_id", "tax.country"))
async def tax_checksum(ctx: object) -> list[Finding]:
    country = str(ctx.value("tax.country"))  # type: ignore[attr-defined]
    tax_id = str(ctx.value("tax.tax_id") or "")  # type: ignore[attr-defined]
    findings: list[Finding] = []
    if country == "IN":
        res = validate_gstin(tax_id)
        if not res.valid and res.reason == "BAD_CHECKSUM":
            findings.append(
                _fail(
                    ctx,
                    "C-TAX-02",
                    "TAX_CHECKSUM_INVALID",
                    "GSTIN checksum invalid",
                    f"GSTIN {tax_id!r} failed checksum.",
                    ["tax.tax_id"],
                )
            )
    elif country in ("GB", "DE"):
        res = validate_vat(tax_id, country)
        if not res.valid and res.reason == "BAD_CHECKSUM":
            findings.append(
                _fail(
                    ctx,
                    "C-TAX-02",
                    "TAX_CHECKSUM_INVALID",
                    "VAT checksum invalid",
                    f"VAT {tax_id!r} failed checksum.",
                    ["tax.tax_id"],
                )
            )
    return findings


@check(id="C-TAX-03", stage="S3", version=1, mandatory=True, reads=("tax.tax_id", "tax.country"))
async def tax_country_shape(ctx: object) -> list[Finding]:
    country = str(ctx.value("tax.country"))  # type: ignore[attr-defined]
    tax_id = str(ctx.value("tax.tax_id") or "")  # type: ignore[attr-defined]
    shape = _looks_like(tax_id)
    expected = {"US": "EIN", "IN": "GSTIN", "GB": "VAT", "DE": "VAT"}.get(country)
    if shape and expected and shape != expected:
        hint = {
            "IN": "India vendors provide a 15-character GSTIN and a PAN.",
            "US": "US vendors provide an EIN (XX-XXXXXXX).",
        }.get(country, "")
        return [
            _fail(
                ctx,
                "C-TAX-03",
                "TAX_FORMAT_MISMATCH",
                "Tax ID shape belongs to another country",
                f"Country is {country} but the value looks like {shape}. {hint}",
                ["tax.tax_id", "tax.country"],
            )
        ]
    return []


@check(
    id="C-TAX-04",
    stage="S3",
    version=1,
    mandatory=True,
    reads=("tax.tax_id", "tax.secondary_ids.PAN"),
)
async def gstin_pan(ctx: object) -> list[Finding]:
    tax_id = str(ctx.value("tax.tax_id") or "")  # type: ignore[attr-defined]
    pan = str(ctx.value("tax.secondary_ids.PAN") or "")  # type: ignore[attr-defined]
    if len(tax_id) == 15 and pan and tax_id[2:12].upper() != pan.upper():
        f = _fail(
            ctx,
            "C-TAX-04",
            "GSTIN_PAN_MISMATCH",
            "GSTIN-embedded PAN differs from declared PAN",
            f"GSTIN chars 3-12 are {tax_id[2:12]!r} but declared PAN is {pan!r}.",
            ["tax.tax_id", "tax.secondary_ids.PAN"],
            severity=Severity.HARD,
            tags={"BANK_ID": 0.3},
        )
        return [f]
    return []


@check(
    id="C-TAX-05",
    stage="S3",
    version=1,
    mandatory=True,
    reads=("tax.tax_id", "company.registered_address.region"),
)
async def gstin_state(ctx: object) -> list[Finding]:
    tax_id = str(ctx.value("tax.tax_id") or "")  # type: ignore[attr-defined]
    if len(tax_id) == 15:
        return []  # region free-text can't be mapped to state code in Phase 1
    return []


@check(
    id="C-TAX-06",
    stage="S3",
    version=1,
    mandatory=True,
    reads=("tax.form_type", "tax.country", "company.country"),
)
async def tax_form(ctx: object) -> list[Finding]:
    form = str(ctx.value("tax.form_type") or "")  # type: ignore[attr-defined]
    country = str(ctx.value("tax.country") or "")  # type: ignore[attr-defined]
    company = str(ctx.value("company.country") or "")  # type: ignore[attr-defined]
    if company == "US" and country == "US" and form.startswith("W8"):
        return [
            _fail(
                ctx,
                "C-TAX-06",
                "TAX_FORM_MISMATCH",
                "Wrong tax form for US vendor",
                "US vendors provide Form W-9, not a W-8.",
                ["tax.form_type"],
            )
        ]
    if company != "US" and form == "W9":
        return [
            _fail(
                ctx,
                "C-TAX-06",
                "TAX_FORM_MISMATCH",
                "Wrong tax form for foreign vendor",
                "Foreign vendors provide a W-8 form, not W-9.",
                ["tax.form_type"],
            )
        ]
    return []


@check(
    id="C-TAX-07",
    stage="S3",
    version=1,
    mandatory=True,
    reads=("tax.secondary_ids.PAN", "company.entity_type"),
)
async def pan_entity(ctx: object) -> list[Finding]:
    pan = str(ctx.value("tax.secondary_ids.PAN") or "")  # type: ignore[attr-defined]
    entity = str(ctx.value("company.entity_type") or "").upper()  # type: ignore[attr-defined]
    if len(pan) == 10:
        res = validate_pan(pan)
        if res.valid:
            fourth = pan[3].upper()
            is_corp_like = any(
                k in entity
                for k in ("LTD", "LIMITED", "PVT", "CORP", "INC", "LLC", "GMBH", "PLC", "AG")
            )
            if fourth == "P" and is_corp_like:
                return [
                    _fail(
                        ctx,
                        "C-TAX-07",
                        "PAN_ENTITY_MISMATCH",
                        "PAN indicates individual, entity is a company",
                        f"PAN 4th character is 'P' (individual) but entity type is {entity}.",
                        ["tax.secondary_ids.PAN", "company.entity_type"],
                    )
                ]
            if fourth in ("C", "F") and "SOLE" in entity:
                return [
                    _fail(
                        ctx,
                        "C-TAX-07",
                        "PAN_ENTITY_MISMATCH",
                        "PAN indicates company, entity is sole prop",
                        f"PAN 4th character is {fourth!r} but entity type is {entity}.",
                        ["tax.secondary_ids.PAN", "company.entity_type"],
                    )
                ]
    return []
