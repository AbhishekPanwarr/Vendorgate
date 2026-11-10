import json
from pathlib import Path

from backend.app.main import create_app


def test_openapi_snapshot():
    app = create_app()
    spec = app.openapi()
    snap = Path("backend/tests/contract/fixtures/openapi.json")
    if not snap.exists():
        snap.write_text(json.dumps(spec, indent=1, sort_keys=True))
    expected = json.loads(snap.read_text())
    assert json.dumps(spec, sort_keys=True) == json.dumps(expected, sort_keys=True)
