"""apply_adjudication: the ONLY path where an LLM verdict lowers severity."""

from backend.app.domain.enums import FixedBy
from backend.app.domain.enums import Outcome
from backend.app.domain.enums import Severity
from backend.app.domain.models import Evidence
from backend.app.domain.models import Finding


def llm_evidence(verdict: object) -> Evidence:
    data: dict[str, object] = {}
    dump = getattr(verdict, "model_dump", None)
    if callable(dump):
        data = dump()
    elif isinstance(verdict, dict):
        data = dict(verdict)
    return Evidence(
        kind="llm",
        ref="L3",
        summary=f"adjudication {data.get('label')} conf {data.get('confidence')}",
        data={k: v for k, v in data.items() if k != "rationale"},
    )


def corroborator_evidence(name: str, summary: str) -> Evidence:
    return Evidence(kind="claim", ref=name, summary=summary)


def apply_adjudication(finding: Finding, verdict: object, corroborators: list[Evidence]) -> Finding:
    """B §9.S8 verbatim. Never clears sanctions (caller must not route SAN/* here)."""
    data = verdict.model_dump() if hasattr(verdict, "model_dump") else {}
    if (
        data.get("label") in ("SAME", "LIKELY_SAME")
        and len(corroborators) >= 1
        and float(data.get("confidence", 0)) >= 0.7
        and bool(data.get("order_swap_consistent"))
    ):
        reason = (
            "NAME_VARIANT_EXPLAINED"
            if finding.check_id.startswith("C-NAME")
            else "NAME_VARIANT_EXPLAINED"
        )
        lowered = finding.model_copy(
            update={
                "outcome": Outcome.WARN,
                "severity": Severity.INFO,
                "reason_code": reason,
                "deterministic": False,
                "fixed_by": FixedBy.NONE,
                "score_tags": {"BANK_ID": 0.15},
                "evidence": finding.evidence + [llm_evidence(verdict)] + corroborators,
            }
        )
        return lowered
    return finding.model_copy(update={"evidence": finding.evidence + [llm_evidence(verdict)]})
