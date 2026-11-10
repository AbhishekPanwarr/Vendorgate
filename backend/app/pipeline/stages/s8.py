"""S8 gray-zone adjudication (bounded LLM; sanctions never routed here)."""

from typing import Any

from backend.app.decision.adjudication import apply_adjudication
from backend.app.decision.adjudication import corroborator_evidence
from backend.app.domain.models import Evidence


def _k3(ctx: Any, variant: str, cfg: dict) -> list[dict[str, str]]:
    """K3: official registration doc whose grounded legal name ~= variant."""
    from backend.app.matching.name_compare import compare_names as _cmp
    from backend.app.matching.name_compare import parse_name as _parse

    out: list[dict[str, str]] = []
    for path, claim in ctx.claims.items():
        if not path.startswith("doc:"):
            continue
        if path.split(".")[-1] not in ("legal_name", "business_name"):
            continue
        if not claim.value:
            continue
        if _cmp(_parse(variant), _parse(str(claim.value)), cfg).relation in ("EXACT", "EQUIVALENT"):
            out.append({"name": "K3", "summary": f"{path} names {claim.value!r}"})
    return out


async def resolve_request(ctx: Any, req: dict[str, Any], model: str) -> dict[str, Any]:
    from backend.app.llm.factory import llm_model
    from backend.app.llm.tasks_l3 import adjudicate
    from backend.app.llm.tasks_l3 import adjudication_user

    model = model or llm_model(False)
    det = req.get("deterministic", {})
    u1 = adjudication_user(
        req["a"],
        req.get("source_a", ""),
        req["b"],
        req.get("source_b", ""),
        req.get("country", ""),
        det,
    )
    u2 = adjudication_user(
        req["b"],
        req.get("source_b", ""),
        req["a"],
        req.get("source_a", ""),
        req.get("country", ""),
        det,
    )
    try:
        v1 = await adjudicate(ctx.llm, model, u1)
        v2 = await adjudicate(ctx.llm, model, u2)
    except Exception:
        return {"verdict": None, "llm_unavailable": True}
    d1 = v1.model_dump()
    d2 = v2.model_dump()
    swap_ok = d1.get("label") in ("SAME", "LIKELY_SAME") and d2.get("label") in (
        "SAME",
        "LIKELY_SAME",
    )
    d1["order_swap_consistent"] = swap_ok
    if not swap_ok:
        d1["label"] = "UNSURE"
    from backend.app.llm.tasks_other import AdjudicationVerdict

    return {"verdict": AdjudicationVerdict(**d1), "llm_unavailable": False}


async def run_s8(ctx: Any) -> list[dict[str, Any]]:
    """Derive adjudication requests from gray-zone findings, then resolve them.

    Derivation (not the S5 checks) owns enqueueing so cache hits, which skip
    check bodies, still adjudicate identically.
    """
    from backend.app.llm.factory import llm_model
    from backend.app.matching.name_compare import compare_names
    from backend.app.matching.name_compare import parse_name

    derived: list[dict[str, Any]] = []
    for f in ctx.findings:
        if f.check_id == "C-NAME-02" and f.reason_code in (
                "LEGAL_FORM_UNCONFIRMED", "NAME_UNCONFIRMED"):
            claims = {c.path: c for c in ctx.claims.values()}
            legal = claims.get("company.legal_name")
            holder = claims.get("bank.account_holder_name")
            if legal is None or holder is None:
                continue
            cfg = dict(ctx.policy.raw["base"]["matching"]["name"])
            comp = compare_names(parse_name(str(legal.value or "")),
                                 parse_name(str(holder.value or "")), cfg)
            if comp.relation not in ("FORM_CONFLICT", "CORE_FUZZY"):
                continue
            corrs = _k3(ctx, str(holder.value or ""), cfg)
            cc = claims.get("company.country")
            derived.append({
                "check_id": "C-NAME-02", "a": str(legal.value or ""),
                "source_a": "form", "b": str(holder.value or ""),
                "source_b": "bank",
                "country": str(cc.value) if cc is not None and cc.value else "",
                "subject": f.subject, "corroborators": corrs,
                "deterministic": {"core_similarity": comp.core_sim,
                                  "legal_form_relation": comp.form_rel}})
    reports = []
    for req in derived:
        if str(req.get("check_id", "")).startswith("C-SAN"):
            reports.append(
                {"check_id": req.get("check_id"), "skipped": "sanctions-never-adjudicated"}
            )
            continue
        rep = await resolve_request(ctx, req, llm_model(False))
        verdict = rep.get("verdict")
        if verdict is None:
            ctx.emit(
                {
                    "type": "adjudication.completed",
                    "check_id": req.get("check_id"),
                    "llm_unavailable": True,
                }
            )
            reports.append({"check_id": req.get("check_id"), "llm_unavailable": True})
            continue
        corrs = [
            corroborator_evidence(c["name"], c["summary"]) for c in req.get("corroborators", [])
        ]
        for i, f in enumerate(ctx.findings):
            if f.check_id == req.get("check_id") and (f.subject or "") == (
                req.get("subject") or ""
            ):
                ctx.findings[i] = apply_adjudication(f, verdict, corrs)
        ctx.emit(
            {
                "type": "adjudication.completed",
                "check_id": req.get("check_id"),
                "label": verdict.model_dump().get("label"),
            }
        )
        reports.append(
            {"check_id": req.get("check_id"), "label": verdict.model_dump().get("label")}
        )
    return reports
