"""Check authoring helper."""

from typing import Any

from backend.app.domain.enums import FixedBy
from backend.app.domain.enums import Outcome
from backend.app.domain.enums import Severity
from backend.app.domain.models import Evidence
from backend.app.domain.models import Finding
from backend.app.domain.models import FixAction


def make_finding(
    ctx: object,
    check_id: str,
    stage: str,
    version: int,
    *,
    outcome: Outcome,
    severity: Severity = Severity.INFO,
    reason_code: str | None = None,
    title: str = "",
    detail: str = "",
    claim_paths: list[str] | None = None,
    fix: FixAction | None = None,
    fixed_by: FixedBy = FixedBy.NONE,
    mandatory: bool = True,
    score_tags: dict[str, float] | None = None,
    subject: str | None = None,
) -> Finding:
    evidence = [Evidence(kind="claim", ref=p, summary=f"claim {p}") for p in (claim_paths or [])]
    if not evidence:
        evidence = [Evidence(kind="rule", ref=check_id, summary=title or check_id)]
    return Finding(
        check_id=check_id,
        stage=stage,
        check_version=version,
        subject=subject,
        outcome=outcome,
        severity=severity,
        reason_code=reason_code,
        title=title or check_id,
        detail=detail,
        evidence=evidence,
        fix=fix,
        fixed_by=fixed_by,
        mandatory=mandatory,
        deterministic=True,
        reads=list(check_reads(ctx, claim_paths or [])),
        score_tags=dict(score_tags or {}),
    )


def check_reads(ctx: Any, paths: list[str]) -> list[str]:
    return list(paths)


def sstr(value: object) -> str:
    return "" if value is None else str(value)
