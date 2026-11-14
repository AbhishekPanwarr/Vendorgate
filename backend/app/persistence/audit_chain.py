"""Hash-chained audit log."""

from backend.app.core.hashing import canonical_json
from backend.app.core.hashing import sha256_hex

GENESIS = "GENESIS"


def entry_hash(prev_hash: str, body_canonical: str) -> str:
    return sha256_hex(prev_hash + body_canonical)


def append_event(
    case_id: str,
    seq: int,
    ts: str,
    actor: str,
    type: str,
    payload: dict[str, object],
    prev_hash: str,
) -> dict[str, object]:
    body = canonical_json(
        {"case_id": case_id, "seq": seq, "ts": ts, "actor": actor, "type": type, "payload": payload}
    )
    return {
        "case_id": case_id,
        "seq": seq,
        "ts": ts,
        "actor": actor,
        "type": type,
        "payload": payload,
        "body_canonical": body,
        "prev_hash": prev_hash,
        "entry_hash": entry_hash(prev_hash, body),
    }


def verify_chain(events: list[dict[str, object]]) -> dict[str, object]:
    h: str = GENESIS
    for e in events:  # e: dict[str, object]
        body: str = canonical_json(
            {
                "case_id": e["case_id"],
                "seq": e["seq"],
                "ts": e["ts"],
                "actor": e["actor"],
                "type": e["type"],
                "payload": e["payload"],
            }
        )
        if entry_hash(h, body) != str(e["entry_hash"]):
            return {"ok": False, "broken_at": int(str(e["seq"])), "length": len(events)}
        h = str(e["entry_hash"])
    return {"ok": True, "length": len(events)}
