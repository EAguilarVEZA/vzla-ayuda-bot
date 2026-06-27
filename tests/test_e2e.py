"""End-to-end journeys through the real bot.handle()."""
import os
import tempfile
import importlib

import pytest


@pytest.fixture()
def bot(monkeypatch):
    path = os.path.join(tempfile.mkdtemp(), "e2e.db")
    monkeypatch.setenv("DB_PATH", path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")  # keyword/numeric routing only
    import app.config as config; importlib.reload(config)
    import app.matching as M; importlib.reload(M)
    import app.bot as bot; importlib.reload(bot)
    bot.M.init_db()
    return bot


def run(bot, u, steps):
    r = None
    for s in steps:
        r = bot.handle(u, s)
    return r


def test_onboarding_to_menu(bot):
    r = run(bot, "u1", ["hola", "1"])           # choose Spanish
    assert "Buscar a una persona" in r          # grouped menu rendered


def test_kb_shelter(bot):
    r = run(bot, "u2", ["hola", "1", "3"])
    assert "Refugio" in r and "VERIFICAR" not in r


def test_missing_persons_search_flow(bot):
    run(bot, "u3", ["hola", "1"])
    bot.handle("u3", "1")                        # -> ask name
    r = bot.handle("u3", "María Pérez, 34, La Guaira")
    assert "Resultados para" in r and "familylinks.icrc.org" in r


def test_cross_border_match_journey(bot):
    # US volunteer offers remote translation (English)
    run(bot, "us", ["hola", "2", "8", "help", "translation", "remote", "USA",
                     "I can translate medical docs", "+1-678", "yes"])
    # VE person needs it (Spanish) -> matches, tagged cross-border
    r = run(bot, "ve", ["hola", "1", "8", "necesito", "traduccion", "remota",
                         "Venezuela", "Necesito traducir", "+58-412", "si"])
    assert "coincidencia" in r.lower()
    assert "frontera" in r.lower()              # cross-border tag
    assert "+1-678" in r                        # the US offer's contact


def test_commands_round_trip(bot):
    run(bot, "u4", ["hola", "2"])
    assert "SHARE" in bot.handle("u4", "menu") or "share" in bot.handle("u4", "share").lower()
    assert "ON" in bot.handle("u4", "alerts")
    assert "resolved" in bot.handle("u4", "resolved").lower()
    # delete wipes and resets to onboarding next time
    bot.handle("u4", "delete")
    assert "idioma" in bot.handle("u4", "hola").lower()
