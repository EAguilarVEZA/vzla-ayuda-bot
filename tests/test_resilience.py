"""Resilience: the bot never crashes a reply, and the webhook always 200s."""
import os
import tempfile
import importlib

import pytest


@pytest.fixture()
def bot(monkeypatch):
    path = os.path.join(tempfile.mkdtemp(), "res.db")
    monkeypatch.setenv("DB_PATH", path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    import app.config as config; importlib.reload(config)
    import app.matching as M; importlib.reload(M)
    import app.bot as bot; importlib.reload(bot)
    bot.M.init_db()
    return bot


def test_handle_never_raises_on_weird_input(bot):
    for body in ["", "   ", "\n\n", "💥🔥", "a" * 5000, "'; DROP TABLE users;--",
                 "{}", "null", "12345678901234567890", "MENU MENU MENU"]:
        out = bot.handle("u", body)
        assert isinstance(str(out), str) and str(out)  # always a non-empty reply


def test_corrupt_session_does_not_crash(bot):
    bot.M.set_lang("u", "es")
    bot.M.set_session("u", "net:desc", "{not valid json")   # corrupted blob
    out = bot.handle("u", "anything")
    assert str(out)                                         # recovered, no crash


def test_internal_error_returns_friendly_fallback(bot, monkeypatch):
    monkeypatch.setattr(bot, "_handle", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    out = bot.handle("u", "hola")
    assert "MENU" in out                                    # error_generic fallback


def test_rate_limit_blocks_excess_posts(bot):
    u = "spammer"
    bot.M.set_lang(u, "es")
    for i in range(bot.POST_LIMIT_PER_DAY):
        bot.M.add_post(u, "offer", "insumos", "remoto", "US", None, "x", "x", "c", 1)
    # 6th attempt via the flow should be rate-limited at consent
    bot.M.set_session(u, "net:consent",
                      '{"kind":"offer","category":"insumos","mode":"remoto","region":"US","contact":"c"}')
    out = bot.handle(u, "si")
    assert "límite" in out.lower() or "limit" in out.lower()


def test_webhook_always_returns_200(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "w.db"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    import app.config as config; importlib.reload(config)
    import app.matching as M; importlib.reload(M)
    import app.bot as bot; importlib.reload(bot)        # rebind to reloaded config/db
    import app.main as main; importlib.reload(main)
    from starlette.testclient import TestClient
    with TestClient(main.app) as c:                     # context fires startup -> init_db
        assert c.post("/whatsapp", data={"From": "whatsapp:+1", "Body": "hola"}).status_code == 200
        # forced internal error still 200 with a fallback message
        monkeypatch.setattr(main, "handle",
                            lambda **k: (_ for _ in ()).throw(RuntimeError("boom")))
        r = c.post("/whatsapp", data={"From": "whatsapp:+1", "Body": "x"})
        assert r.status_code == 200 and "try again" in r.text.lower()
