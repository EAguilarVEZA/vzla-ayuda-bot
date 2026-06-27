"""Org portal: partner keys, capacity push -> bot, claims."""
import os
import tempfile
import importlib

import pytest


@pytest.fixture()
def ctx(monkeypatch):
    path = os.path.join(tempfile.mkdtemp(), "p.db")
    monkeypatch.setenv("DB_PATH", path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    import app.config as config; importlib.reload(config)
    import app.matching as M; importlib.reload(M)
    import app.partners as P; importlib.reload(P)
    M.init_db()
    return M, P


def test_partner_key_auth(ctx):
    M, P = ctx
    key = P.create_partner("Direct Relief")
    assert key.startswith("vzla_")
    assert P.get_partner(key)["name"] == "Direct Relief"
    assert P.get_partner("nope") is None
    assert P.get_partner("") is None


def test_capacity_push_and_filter(ctx):
    M, P = ctx
    P.add_capacity("Caritas", "shelter", "La Guaira", "Refugio San José", "120 spaces", "open")
    P.add_capacity("Caritas", "medical", "Caracas", "Clinic", "", "full")
    shelters = P.list_capacity(type_="shelter")
    assert len(shelters) == 1 and shelters[0]["location"] == "La Guaira"
    assert P.list_capacity(type_="shelter", location="caracas") == []


def test_claims(ctx):
    M, P = ctx
    P.add_claim("Team Rubicon", "medical", "La Guaira", "surgical kits")
    rows = P.list_claims(category="medical")
    assert rows and rows[0]["partner"] == "Team Rubicon"


def test_capacity_surfaces_in_bot_kb_reply(ctx):
    M, P = ctx
    import app.bot as bot; importlib.reload(bot)
    # nothing yet
    assert "Live availability" not in bot._live_capacity("shelter", "en")
    P.add_capacity("Caritas", "shelter", "La Guaira", "Refugio San José", "120 spaces", "open")
    out = bot._live_capacity("shelter", "en")
    assert "Refugio San José" in out and "La Guaira" in out
    # full sites are hidden
    P.add_capacity("X", "shelter", "Catia", "Full site", "", "full")
    assert "Full site" not in bot._live_capacity("shelter", "en")
