"""Tier helpers (provisional tier shared by S2 and S9)."""


def spend_raw(annual_usd: float, policy: object) -> float:
    bands = policy.raw["base"]["scoring"]["spend_bands_usd"]  # type: ignore[attr-defined]
    for limit, raw in bands:
        if limit is None or annual_usd < limit:
            return float(raw)
    return 1.0


def provisional_tier(annual_usd: float, category: str, country: str, policy: object) -> str:
    raw = spend_raw(annual_usd, policy)
    cat = policy.raw["base"]["scoring"]["category_risk"].get(category, 0.4)  # type: ignore[attr-defined]
    if annual_usd >= 500000 or (raw >= 0.8 and cat >= 0.6):
        return "HIGH"
    if raw >= 0.5 or cat >= 0.6:
        return "MEDIUM"
    return "LOW"


def band(total: float, policy: object) -> str:
    bands = policy.raw["base"]["scoring"]["bands"]  # type: ignore[attr-defined]
    if total < bands["low_max"]:
        return "LOW"
    if total <= bands["medium_max"]:
        return "MEDIUM"
    return "HIGH"
