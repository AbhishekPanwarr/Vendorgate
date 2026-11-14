"""S11 comms: items, templates, checker (pre-outbox gate), outbox."""

from typing import Any

INTERNAL_ONLY_CODES = {
    "SANCTIONS_MATCH",
    "SANCTIONS_REVIEW",
    "PEP_REVIEW",
    "ADVERSE_MEDIA_REVIEW",
    "BANK_SHARED_ACROSS_VENDORS",
    "TIN_REUSE_DIFFERENT_NAME",
    "CLUSTER_REVIEW",
    "DOC_INJECTION_SUSPECTED",
    "CHANGE_VELOCITY",
    "DUPLICATE_REVIEW",
    "DUPLICATE_EXISTING",
    "RELATED_PARTY_PROOF_REQUIRED",
    "SANCTIONED_OWNERSHIP",
    "EMBARGOED_JURISDICTION",
    "LIQUIDATION_REVIEW",
    "CALLBACK_REQUIRED",
    "BANK_CHANGE_REQUIRES_CALLBACK",
    "TIER_APPROVAL_REQUIRED",
}

FORBIDDEN = {"sanction", "ofac", "watchlist", "fraud", "suspicious", "blacklist", "pep", "embargo"}


def build_items(decision: dict[str, Any], findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = []
    for f in findings:
        if f.get("outcome") != "FAIL":
            continue
        if f.get("fixed_by") != "VENDOR":
            continue
        fix = f.get("fix") or {}
        code = fix.get("code", f.get("check_id"))
        items.append(
            {
                "fix_code": code,
                "title": f.get("title", ""),
                "what": f.get("detail", ""),
                "how_to_fix": f"See guidance for {code}.",
                "field_paths": fix.get("field_paths", []),
                "reason_code": f.get("reason_code"),
            }
        )
    return items


def render_vendor_email(
    status: str,
    vendor_name: str,
    items: list[dict[str, Any]],
    due: str,
    internal_only: bool = False,
) -> dict[str, str]:
    if status == "APPROVED":
        return {
            "subject": f"{vendor_name} — onboarding complete",
            "body": f"Hi, {vendor_name} is approved and ready for purchase orders.",
        }
    if status == "REJECTED" or internal_only:
        return {
            "subject": f"{vendor_name} — onboarding update",
            "body": (
                "Hi, we are unable to complete onboarding at this time. "
                "It is under compliance review. "
                f"You may appeal by replying before {due}. "
                f"[Resubmit → /resubmit]"
            ),
        }
    lines = [
        f"Hi, thanks for submitting details for {vendor_name}.",
        "Please fix the following items:",
    ]
    for i, it in enumerate(items, 1):
        lines.append(f"{i}. [[{it['fix_code']}]] {it['title']}: {it['what']}")
    lines.append(f"Please resubmit by {due}. [Resubmit → /resubmit]")
    body = "\n".join(lines)
    return {"subject": f"{vendor_name} — action needed to complete onboarding", "body": body}


def check_message(
    subject: str,
    body: str,
    items: list[dict[str, Any]],
    internal_only: bool = False,
    status: str = "PENDING",
) -> list[str]:
    errors = []
    if not internal_only:
        import re

        wanted = {it["fix_code"] for it in items}
        for it in items:
            tag = f"[[{it['fix_code']}]]"
            if body.count(tag) != 1:
                errors.append(f"fix {it['fix_code']} must appear exactly once")
        for extra in set(re.findall(r"\[\[([A-Z0-9_]+)\]\]", body)):
            if extra not in wanted:
                errors.append(f"extra fix {extra} not required")
    low = (subject + " " + body).lower()
    for term in FORBIDDEN:
        if term in low:
            errors.append(f"forbidden term: {term}")
    if status != "APPROVED" and "/resubmit" not in body:
        errors.append("missing resubmit link")
    if len(body.split()) > 350:
        errors.append("message over 350 words")
    return errors


def compose(
    decision: dict[str, Any], findings: list[dict[str, Any]], vendor_name: str, due: str
) -> dict[str, Any]:
    status = decision.get("status", "PENDING")
    codes = set(decision.get("reason_codes", []))
    internal_only = bool(codes & INTERNAL_ONLY_CODES) or status == "REJECTED"
    items = [] if internal_only else build_items(decision, findings)
    msg = render_vendor_email(status, vendor_name, items, due, internal_only)
    errors = check_message(msg["subject"], msg["body"], items, internal_only, status)
    if errors and not internal_only:
        # fall back to plain template (never block the run)
        msg = render_vendor_email(status, vendor_name, items, due, internal_only)
    return {
        "subject": msg["subject"],
        "body": msg["body"],
        "items": items,
        "checker_errors": errors,
        "internal_only": internal_only,
    }
