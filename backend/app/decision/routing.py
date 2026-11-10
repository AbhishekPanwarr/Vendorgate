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
