"""Trust & safety: screening, minor protection, blocks, bans, verification."""
import os
import tempfile
import importlib

import pytest

from app import trust


# --- deterministic screening (no network) ----------------------------------
def test_screen_blocks_advance_payment():
    ok, reason = trust.screen_deterministic("Te ayudo pero envía dinero por Zelle primero")
    assert not ok and reason == "money"


def test_screen_blocks_sexual_and_lure():
    assert trust.screen_deterministic("manda fotos intimas")[1] == "sexual"
    assert trust.screen_deterministic("escríbeme a Telegram para coordinar")[1] == "lure"


def test_screen_allows_normal_offer():
    ok, reason = trust.screen_deterministic("Puedo llevar insumos médicos a La Guaira")
    assert ok and reason is None


def test_detect_minor():
    assert trust.detect_minor("busco a mi hija de 8 años")
    assert trust.detect_minor("there is a child alone here")
    assert not trust.detect_minor("necesito agua potable en Caracas")


# --- matching-level enforcement --------------------------------------------
@pytest.fixture()
def M(monkeypatch):
    path = os.path.join(tempfile.mkdtemp(), "t.db")
    monkeypatch.setenv("DB_PATH", path)
    import app.config as config
    importlib.reload(config)
    import app.matching as matching
    importlib.reload(matching)
    matching.init_db()
    return matching


def test_blocked_contact_is_hidden_from_viewer(M):
    M.add_post("bad", "offer", "traduccion", "remoto", "US", None, "x", "x", "+1-555", 1)
    viewer = "ve1"
    assert M.find_matches("need", "traduccion", "remoto", "VE", None, viewer=viewer)
    M.add_block(viewer, "+1-555")
    assert M.find_matches("need", "traduccion", "remoto", "VE", None, viewer=viewer) == []


def test_banned_author_posts_excluded_and_suspended(M):
    M.add_post("troll", "offer", "insumos", "remoto", "US", None, "x", "x", "c", 1)
    M.ban_user("troll", "spam")
    assert M.is_banned("troll")
    assert M.find_matches("need", "insumos", "remoto", "VE", None) == []


def test_report_suspends_contact_posts(M):
    M.add_post("u", "offer", "insumos", "remoto", "US", None, "x", "x", "+1999", 1)
    M.add_report("victim", "+1999", "user_report", "asked me for money")
    M.suspend_posts_by_contact("+1999")
    assert M.find_matches("need", "insumos", "remoto", "VE", None) == []
    assert M.moderation_summary()["suspended_posts"] == 1


def test_verified_helper_sorts_first(M):
    M.add_post("plain", "offer", "busqueda", "remoto", "US", None, "x", "x", "c1", 1)
    M.add_post("org", "offer", "busqueda", "remoto", "US", None, "x", "x", "c2", 1)
    M.set_verified("org", True)
    matches = M.find_matches("need", "busqueda", "remoto", "VE", None)
    assert matches[0]["user"] == "org" and matches[0]["_verified"] is True
