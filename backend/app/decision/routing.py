"""SoD routing guard."""


def check_sod(case_requester: str, actor: str, role: str) -> bool:
    """True if allowed. Approver must differ from requester."""
    if role in ("CONTROLLER", "COMPLIANCE", "AP_ANALYST") and actor == case_requester:
        return False
    return True


def resolve_allowed(reason_code: str, role: str, policy: object) -> bool:
    table = policy.raw["base"].get("resolvable_by", {})  # type: ignore[attr-defined]
    allowed = table.get(reason_code)
    if allowed is None:
        return role in ("AP_ANALYST", "CONTROLLER", "COMPLIANCE")
    return role in allowed


ALLOWED_SOURCES = {"VENDOR_MASTER", "REGISTRY", "PUBLIC_DIRECTORY"}


def check_callback(
    number_used: str,
    number_source: str,
    request_phones: list[str],
    number_age_days: int,
    min_age_days: int,
    attested: bool,
) -> dict[str, object]:
    """Pure independence rule (enforced here, not in the API layer)."""
    if not attested:
        return {"ok": False, "reason": "ATTESTATION_REQUIRED"}
    if number_used in set(request_phones):
        return {"ok": False, "reason": "CALLBACK_NOT_INDEPENDENT"}
    if number_source not in ALLOWED_SOURCES:
        return {"ok": False, "reason": "CALLBACK_NOT_INDEPENDENT"}
    if number_age_days < min_age_days:
        return {"ok": False, "reason": "CALLBACK_NUMBER_TOO_NEW"}
    return {"ok": True, "reason": ""}
