# ADR 0008 — Python runtime pin
## Context
Spec pins >=3.12,<3.13; local env is 3.13.5; `make ci` must run locally.
## Decision
Spec loosened to >=3.12,<3.14; CI matrix + Docker pin 3.12; no 3.13 CI job (avoids third-party 3.13 warning noise under filterwarnings=error).
## Consequences
Local 3.13 runs tests; 3.12 is the runtime that matters (Docker/CI).
## Alternatives Considered
`uv python install 3.12` in make setup — rejected: extra failure mode.
