"""Tests for the privacy-preserving analytics layer."""
import os
import tempfile
import importlib

import pytest


@pytest.fixture()
def fresh_db(monkeypatch):
    path = os.path.join(tempfile.mkdtemp(), "a.db")
    monkeypatch.setenv("DB_PATH", path)
    import app.config as config
    importlib.reload(config)
    import app.matching as M
    importlib.reload(M)
    import app.analytics as A
    importlib.reload(A)
    M.init_db()
    return M, A


def test_event_stores_no_pii(fresh_db):
    M, A = fresh_db
    A.log_event("whatsapp:+58412555", "shelter", region="VE",
                location="La Guaira", lang="es")
    with M._conn() as c:
        row = dict(c.execute("SELECT * FROM events").fetchone())
    # the raw phone number must never appear in the row
    assert "whatsapp" not in str(row).lower()
    assert "+58412555" not in str(row)
    assert row["intent"] == "shelter" and row["location"] == "La Guaira"
    assert len(row["user_day_hash"]) == 16


def test_user_day_hash_rotates_daily(fresh_db):
    _, A = fresh_db
    h1 = A._user_day_hash("u1", "2026-06-27")
    h2 = A._user_day_hash("u1", "2026-06-28")
    assert h1 != h2                      # not linkable across days
    assert A._user_day_hash("u1", "2026-06-27") == h1  # stable within a day


def test_daily_summary_counts_and_heatmap(fresh_db):
    _, A = fresh_db
    A.log_event("u1", "shelter", region="VE", location="La Guaira", lang="es")
    A.log_event("u2", "shelter", region="VE", location="La Guaira", lang="es")
    A.log_event("u3", "medical", region="VE", location="Caracas", lang="en")
    A.log_event("u1", "menu", lang="es")  # navigation, not a need
    s = A.daily_summary(days=7)
    assert s["totals"]["events"] == 4
    assert s["totals"]["unique_users"] == 3
    assert s["totals"]["needs"] == 3
    top = s["needs_heatmap"][0]
    assert top["location"] == "La Guaira" and top["total"] == 2
    assert dict(s["by_language"]).get("es") == 3


def test_hero_supply_demand_gap(fresh_db):
    M, A = fresh_db
    M.add_post("u1", "need", "traduccion", "remoto", "VE", None, "x", "x", "c", 1)
    M.add_post("u2", "need", "traduccion", "remoto", "VE", None, "x", "x", "c", 1)
    M.add_post("u3", "offer", "traduccion", "remoto", "US", None, "x", "x", "c", 1)
    gaps = A.hero_supply_demand()
    row = next(g for g in gaps if g["category"] == "traduccion")
    assert row["need"] == 2 and row["offer"] == 1 and row["gap"] == 1
