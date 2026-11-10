"""Test isolation: each test gets a fresh SQLite file."""

import os

import pytest


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    from backend.app.persistence import store

    store._engines.clear()
    yield
    for eng in list(store._engines.values()):
        eng.dispose()
    store._engines.clear()
