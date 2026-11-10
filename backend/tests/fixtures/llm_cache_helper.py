"""L1 cache helper: committed fixtures (live-recorded + hand-authored)."""

import json
from pathlib import Path

_CACHE_DIR = Path("backend/tests/fixtures/llm_cache")


def load_cache() -> dict[str, object]:
    store: dict[str, object] = {}
    for path in sorted(_CACHE_DIR.glob("*.json")):
        store.update(json.loads(path.read_text()))
    return store
