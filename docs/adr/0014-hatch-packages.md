# ADR 0014 — Hatch wheel packages for the backend/ layout

## Context

`make setup` (`uv sync --extra dev || pip install -e ".[dev]"`) fails on a
clean checkout: hatch has no `packages` configured, so the wheel build finds
no files. The repo runs from the source tree, which masked the breakage.

## Decision

Declare the existing layout explicitly:

```toml
[tool.hatch.build.targets.wheel]
packages = ["backend"]
```

No code moves; the sdist/wheel now contains the same tree developers run.

## Consequences

`make setup` works on a clean machine. No runtime behavior changes.
