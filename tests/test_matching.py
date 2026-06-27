"""Tests for hero-network matching, incl. cross-border prioritization."""
import os
import tempfile
import importlib

import pytest


@pytest.fixture()
def M(monkeypatch):
    path = os.path.join(tempfile.mkdtemp(), "m.db")
    monkeypatch.setenv("DB_PATH", path)
    import app.config as config
    importlib.reload(config)
    import app.matching as matching
    importlib.reload(matching)
    matching.init_db()
    return matching


def test_cross_border_remote_match_listed_first(M):
    # A same-region remote offer (posted most recently) and a cross-border one.
    M.add_post("us1", "offer", "traduccion", "remoto", "US", None,
               "Translate docs", "Translate docs", "+1", consent=1)
    M.add_post("ve1", "offer", "traduccion", "remoto", "VE", None,
               "Traduzco", "I translate", "+58", consent=1)
    # A VE user needing remote translation help.
    matches = M.find_matches("need", "traduccion", "remoto", "VE", None, limit=5)
    assert matches, "should find remote matches"
    # The US offer (cross-border) must come first even though it's older.
    assert matches[0]["region"] == "US"
    assert matches[0]["_cross_border"] is True


def test_in_person_matches_same_region_only(M):
    M.add_post("atl", "offer", "insumos", "presencial", "US", "Alpharetta",
               "Drop off", "Drop off", "+1", consent=1)
    # In-person need in VE should NOT match a US in-person offer.
    none = M.find_matches("need", "insumos", "presencial", "VE", "Caracas")
    assert none == []
    # In-person need in US/Alpharetta should match.
    hit = M.find_matches("need", "insumos", "presencial", "US", "Alpharetta")
    assert len(hit) == 1 and hit[0]["_cross_border"] is False


def test_consent_required_to_match(M):
    M.add_post("x", "offer", "busqueda", "remoto", "US", None, "help", "help",
               "+1", consent=0)
    assert M.find_matches("need", "busqueda", "remoto", "VE", None) == []
