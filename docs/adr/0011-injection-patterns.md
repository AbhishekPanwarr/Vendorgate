# ADR 0011 — Injection pattern list (versioned)

## Context

C-DOC-08 needs a deterministic pattern list plus hidden-text signals.
Derives from D-3.1/D-3.10.

## Decision

Patterns live in `policy/injection_patterns.yaml` (v1.0, six patterns);
hidden-text detection via pdfplumber char metadata (size < 2pt,
white-on-white). Hit forces human review (FAIL/HARD, INTERNAL); never
auto-rejects. Update cadence: extend via ADR when new variants observed.

## Consequences

EC-5 variants (hidden tiny text, visible instruction text) both fire.

## Alternatives Considered

LLM-only detection — rejected: non-deterministic, bypassable.
