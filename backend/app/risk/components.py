"""Risk components: each returns (raw 0..1, drivers[])."""

from backend.app.risk.tiers import spend_raw


def component_spend(ctx: object, tags: dict[str, float]) -> tuple[float, list[str]]:
    usd = float(ctx.value("requester.expected_annual_spend_usd") or 0)  # type: ignore[attr-defined]
    raw = spend_raw(usd, ctx.policy)  # type: ignore[attr-defined]
    drivers = [f"spend_usd={usd}"]
    if str(ctx.value("requester.one_time")) == "True" and usd >= 25000:  # type: ignore[attr-defined]
        raw += 0.1
        drivers.append("one_time>=25k +0.1")
    return min(raw, 1.0), drivers


def component_geo(ctx: object, tags: dict[str, float]) -> tuple[float, list[str]]:
    country = str(ctx.value("company.country") or "")  # type: ignore[attr-defined]
    raw = float(ctx.policy.raw["base"]["scoring"]["country_risk"].get(country, 0.25))  # type: ignore[attr-defined]
    drivers = [f"country={country}"]
    if str(ctx.value("bank.country")) != country:  # type: ignore[attr-defined]
        raw += 0.3
        drivers.append("bank_country!=company_country +0.3")
    raw += tags.get("GEO", 0.0)
    return min(raw, 1.0), drivers


def component_docs(ctx: object, tags: dict[str, float]) -> tuple[float, list[str]]:
    raw = tags.get("DOCS", 0.0)
    return min(raw, 1.0), ([f"doc_tags={raw}"] if raw else [])


def component_bank_id(ctx: object, tags: dict[str, float]) -> tuple[float, list[str]]:
    raw = 0.1  # first-time account baseline (Phase 1: every submission is new)
    drivers = ["first_time_account +0.1"]
    raw += tags.get("BANK_ID", 0.0)
    return min(raw, 1.0), drivers


def component_category(ctx: object, tags: dict[str, float]) -> tuple[float, list[str]]:
    cat = str(ctx.value("requester.category") or "")  # type: ignore[attr-defined]
    raw = float(ctx.policy.raw["base"]["scoring"]["category_risk"].get(cat, 0.4))  # type: ignore[attr-defined]
    drivers = [f"category={cat}"]
    if str(ctx.value("requester.data_access")) == "True":  # type: ignore[attr-defined]
        raw += 0.3
        drivers.append("data_access +0.3")
    return min(raw, 1.0), drivers


def component_registry_media(ctx: object, tags: dict[str, float]) -> tuple[float, list[str]]:
    return min(tags.get("REGISTRY_MEDIA", 0.0), 1.0), []
