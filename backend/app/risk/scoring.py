"""Risk scoring: score(findings, ctx) -> RiskBreakdown."""

from backend.app.domain.enums import Tier
from backend.app.domain.models import ComponentScore
from backend.app.domain.models import Finding
from backend.app.domain.models import RiskBreakdown
from backend.app.risk import components
from backend.app.risk.tiers import band

_ORDER = ["SPEND", "GEO", "DOCS", "BANK_ID", "CATEGORY", "REGISTRY_MEDIA"]


def score(findings: list[Finding], ctx: object) -> RiskBreakdown:
    tags: dict[str, float] = {}
    for f in findings:
        for comp, delta in (f.score_tags or {}).items():
            tags[comp] = tags.get(comp, 0.0) + float(delta)
    weights = ctx.policy.raw["base"]["scoring"]["weights"]  # type: ignore[attr-defined]
    fns = {
        "SPEND": components.component_spend,
        "GEO": components.component_geo,
        "DOCS": components.component_docs,
        "BANK_ID": components.component_bank_id,
        "CATEGORY": components.component_category,
        "REGISTRY_MEDIA": components.component_registry_media,
    }
    comps: dict[str, ComponentScore] = {}
    total = 0.0
    for name in _ORDER:
        raw, drivers = fns[name](ctx, tags)
        points = round(weights[name] * raw, 4)
        total += points
        comps[name] = ComponentScore(
            weight=float(weights[name]), raw=round(raw, 4), points=points, drivers=drivers
        )
    total = round(total, 2)
    tier = Tier[band(total, ctx.policy)]  # type: ignore[attr-defined]
    return RiskBreakdown(components=comps, total=total, band=tier)
