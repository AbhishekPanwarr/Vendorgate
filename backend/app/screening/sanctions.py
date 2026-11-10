"""Sanctions/PEP/adverse screening ladder (deterministic; no LLM)."""

import json
from pathlib import Path
from typing import Any

_LISTS = Path(__file__).parent / "lists"


def _load(name: str) -> list[dict[str, Any]]:
    path = _LISTS / name
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _aliases(entry: dict[str, Any]) -> list[str]:
    names = entry.get("names") or [""]
    return [str(names[0])] + [str(a) for a in entry.get("aliases", [])]


def secondary_matches(subject: dict[str, Any], entry: dict[str, Any]) -> int:
    score = 0
    if (
        subject.get("country")
        and entry.get("country")
        and str(subject["country"]).upper() == str(entry["country"]).upper()
    ):
        score += 1
    if (
        subject.get("reg_no")
        and entry.get("reg_no")
        and str(subject["reg_no"]) == str(entry["reg_no"])
    ):
        score += 2
    if (
        subject.get("incorporation_year")
        and entry.get("incorporation_year")
        and int(subject["incorporation_year"]) == int(entry["incorporation_year"])
    ):
        score += 1
    return score


def contradictions(subject: dict[str, Any], entry: dict[str, Any]) -> int:
    n = 0
    if (
        subject.get("country")
        and entry.get("country")
        and str(subject["country"]).upper() != str(entry["country"]).upper()
    ):
        n += 1
    if (
        subject.get("incorporation_year")
        and entry.get("incorporation_year")
        and int(subject["incorporation_year"]) != int(entry["incorporation_year"])
    ):
        n += 1
    return n


def screen(
    subject_name: str,
    subject: dict[str, Any],
    entries: list[dict[str, Any]],
    confirm: float = 0.97,
    potential: float = 0.85,
) -> dict[str, Any]:
    from backend.app.matching.name_compare import parse_name
    from backend.app.matching.similarity import core_similarity

    best: dict[str, Any] = {"verdict": "NO_MATCH", "score": 0.0, "entry": None}
    subj = parse_name(subject_name).core
    for entry in entries:
        sims = []
        for alias in _aliases(entry):
            try:
                sims.append(core_similarity(subj, parse_name(alias).core))
            except Exception:
                continue
        s = max(sims) if sims else 0.0
        sec = secondary_matches(subject, entry)
        con = contradictions(subject, entry)
        if s >= confirm:
            if sec >= 1:
                verdict = "CONFIRMED"
            elif con >= 2:
                verdict = "CLEARED_RATIONALE"
            else:
                verdict = "POTENTIAL"
        elif s >= potential:
            verdict = "CLEARED_RATIONALE" if con >= 2 else "POTENTIAL"
        else:
            verdict = "NO_MATCH"
        rank = {"NO_MATCH": 0, "CLEARED_RATIONALE": 1, "POTENTIAL": 2, "CONFIRMED": 3}
        if rank[verdict] > rank[best["verdict"]] or (
            rank[verdict] == rank[best["verdict"]] and s > best["score"]
        ):
            best = {"verdict": verdict, "score": s, "entry": entry}
    return best


def sanctions_entries() -> list[dict[str, Any]]:
    return _load("sanctions_mock.jsonl")


def pep_entries() -> list[dict[str, Any]]:
    return _load("pep_mock.jsonl")


def adverse_entries() -> list[dict[str, Any]]:
    return _load("adverse_mock.jsonl")
