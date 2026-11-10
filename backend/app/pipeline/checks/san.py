"""S7 checks: C-SAN-01..06 (no LLM anywhere in this file)."""

from typing import Any

from backend.app.domain.enums import FixedBy
from backend.app.domain.enums import Outcome
from backend.app.domain.enums import Severity
from backend.app.domain.models import Finding
from backend.app.domain.models import FixAction
from backend.app.pipeline.checks._util import make_finding
from backend.app.pipeline.checks._util import sstr
from backend.app.pipeline.registry import check
from backend.app.screening import sanctions as san

EMBARGOED = {"KP", "IR", "CU", "SY"}


def _subject(ctx: Any) -> dict[str, Any]:
    return {
        "country": sstr(ctx.value("company.country")),
        "reg_no": "",
        "incorporation_year": _year(sstr(ctx.value("company.incorporation_date"))),
    }


def _year(raw: str) -> int:
    try:
        return int(raw[:4])
    except ValueError:
        return 0


def _map_screened(
    check_id: str, ctx: Any, result: dict[str, Any], paths: list[str]
) -> list[Finding]:
    verdict = result["verdict"]
    if verdict == "NO_MATCH":
        return []
    if verdict == "CLEARED_RATIONALE":
        return [
            make_finding(
                ctx,
                check_id,
                "S7",
                1,
                outcome=Outcome.PASS,
                severity=Severity.INFO,
                title="Sanctions decoy cleared",
                detail="High name similarity but contradicting identifiers.",
                claim_paths=paths,
                score_tags={"GEO": 0.1},
            )
        ]
    if verdict == "CONFIRMED":
        return [
            make_finding(
                ctx,
                check_id,
                "S7",
                1,
                outcome=Outcome.FAIL,
                severity=Severity.CRITICAL,
                reason_code="SANCTIONS_MATCH",
                title="Sanctions match confirmed",
                detail="Compliance hold; legal review required.",
                claim_paths=paths,
                fixed_by=FixedBy.NONE,
            )
        ]
    return [
        make_finding(
            ctx,
            check_id,
            "S7",
            1,
            outcome=Outcome.FAIL,
            severity=Severity.HARD,
            reason_code="SANCTIONS_REVIEW",
            title="Possible sanctions match",
            detail="Compliance review required.",
            claim_paths=paths,
            fix=FixAction(code="COMPLIANCE_REVIEW", field_paths=paths),
            fixed_by=FixedBy.INTERNAL,
            score_tags={"GEO": 0.5},
        )
    ]


@check(
    id="C-SAN-01",
    stage="S7",
    version=2,
    mandatory=True,
    reads=("company.legal_name", "company.country", "company.incorporation_date",
           "lists.sanctions_version"),
)
async def san_entity(ctx: Any) -> list[Finding]:
    legal = sstr(ctx.value("company.legal_name"))
    return _map_screened(
        "C-SAN-01",
        ctx,
        san.screen(legal, _subject(ctx), san.sanctions_entries()),
        ["company.legal_name"],
    )


@check(id="C-SAN-02", stage="S7", version=1, mandatory=True, reads=("company.owners.0.name", "company.country", "company.incorporation_date", "lists.sanctions_version"))
async def san_owners(ctx: Any) -> list[Finding]:
    findings: list[Finding] = []
    i = 0
    while True:
        name = ctx.value(f"company.owners.{i}.name")
        if name is None:
            break
        findings.extend(
            _map_screened(
                "C-SAN-02",
                ctx,
                san.screen(str(name), _subject(ctx), san.sanctions_entries()),
                [f"company.owners.{i}.name"],
            )
        )
        i += 1
    return findings


@check(
    id="C-SAN-03", stage="S7", version=2, mandatory=True, reads=("company.country", "bank.country", "lists.sanctions_version")
)
async def embargo(ctx: Any) -> list[Finding]:
    for path in ("company.country", "bank.country"):
        if sstr(ctx.value(path)).upper() in EMBARGOED:
            return [
                make_finding(
                    ctx,
                    "C-SAN-03",
                    "S7",
                    1,
                    outcome=Outcome.FAIL,
                    severity=Severity.CRITICAL,
                    reason_code="EMBARGOED_JURISDICTION",
                    title="Embargoed jurisdiction",
                    detail=f"{path} is embargoed.",
                    claim_paths=[path],
                    fixed_by=FixedBy.NONE,
                )
            ]
    return []


@check(id="C-SAN-04", stage="S7", version=1, mandatory=True, reads=("company.owners.0.name", "company.country", "company.incorporation_date", "lists.sanctions_version"))
async def pep(ctx: Any) -> list[Finding]:
    findings: list[Finding] = []
    i = 0
    while True:
        name = ctx.value(f"company.owners.{i}.name")
        if name is None:
            break
        r = san.screen(str(name), _subject(ctx), san.pep_entries())
        if r["verdict"] in ("CONFIRMED", "POTENTIAL"):
            findings.append(
                make_finding(
                    ctx,
                    "C-SAN-04",
                    "S7",
                    1,
                    outcome=Outcome.FAIL,
                    severity=Severity.HARD,
                    reason_code="PEP_REVIEW",
                    title="PEP-linked owner",
                    detail="Enhanced diligence; not an auto-reject.",
                    claim_paths=[f"company.owners.{i}.name"],
                    fix=FixAction(
                        code="COMPLIANCE_REVIEW", field_paths=[f"company.owners.{i}.name"]
                    ),
                    fixed_by=FixedBy.INTERNAL,
                    score_tags={"GEO": 0.3},
                )
            )
        i += 1
    return findings


@check(id="C-SAN-05", stage="S7", version=1, mandatory=True, reads=("company.legal_name", "lists.sanctions_version"))
async def adverse(ctx: Any) -> list[Finding]:
    legal = sstr(ctx.value("company.legal_name")).lower()
    for entry in san.adverse_entries():
        if (
            str(entry.get("subject", "")).lower() in legal
            or legal in str(entry.get("subject", "")).lower()
        ):
            if not entry.get("subject"):
                continue
            if entry.get("severity") == "HIGH":
                return [
                    make_finding(
                        ctx,
                        "C-SAN-05",
                        "S7",
                        1,
                        outcome=Outcome.FAIL,
                        severity=Severity.HARD,
                        reason_code="ADVERSE_MEDIA_REVIEW",
                        title="Adverse media hit",
                        detail=str(entry.get("summary", "")),
                        claim_paths=["company.legal_name"],
                        fix=FixAction(code="COMPLIANCE_REVIEW", field_paths=["company.legal_name"]),
                        fixed_by=FixedBy.INTERNAL,
                        score_tags={"REGISTRY_MEDIA": 1.0},
                    )
                ]
            return [
                make_finding(
                    ctx,
                    "C-SAN-05",
                    "S7",
                    1,
                    outcome=Outcome.WARN,
                    severity=Severity.INFO,
                    reason_code="ADVERSE_MEDIA_LOW",
                    title="Low-severity adverse media",
                    detail=str(entry.get("summary", "")),
                    claim_paths=["company.legal_name"],
                    score_tags={"REGISTRY_MEDIA": 0.3},
                )
            ]
    return []


@check(id="C-SAN-06", stage="S7", version=1, mandatory=True, reads=("company.owners.0.name", "company.country", "company.incorporation_date", "lists.sanctions_version"))
async def sanctioned_ownership(ctx: Any) -> list[Finding]:
    pct = 0.0
    i = 0
    while True:
        name = ctx.value(f"company.owners.{i}.name")
        if name is None:
            break
        r = san.screen(str(name), _subject(ctx), san.sanctions_entries())
        if r["verdict"] == "CONFIRMED":
            try:
                pct += float(ctx.value(f"company.owners.{i}.ownership_pct") or 0)
            except (TypeError, ValueError):
                pass
        i += 1
    if pct >= 50:
        return [
            make_finding(
                ctx,
                "C-SAN-06",
                "S7",
                1,
                outcome=Outcome.FAIL,
                severity=Severity.CRITICAL,
                reason_code="SANCTIONED_OWNERSHIP",
                title="Sanctioned ownership ≥ 50%",
                detail="Blocked; legal review required.",
                claim_paths=["company.owners.0.name"],
                fixed_by=FixedBy.NONE,
            )
        ]
    return []
