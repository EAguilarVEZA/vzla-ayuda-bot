"""Close-the-loop: resolve, notify-on-match queue, alert subscriptions."""
import os
import tempfile
import importlib

import pytest


@pytest.fixture()
def M(monkeypatch):
    path = os.path.join(tempfile.mkdtemp(), "cl.db")
    monkeypatch.setenv("DB_PATH", path)
    import app.config as config
    importlib.reload(config)
    import app.matching as matching
    importlib.reload(matching)
    matching.init_db()
    return matching


def test_resolve_closes_open_posts(M):
    M.add_post("u", "need", "insumos", "remoto", "VE", None, "x", "x", "c", 1)
    assert M.resolve_user_posts("u") == 1
    # resolved posts no longer match
    assert M.find_matches("offer", "insumos", "remoto", "US", None) == []


def test_notification_queue_delivers_once(M):
    M.add_notification("u", "first")
    M.add_notification("u", "second")
    assert M.has_pending("u")
    got = M.pop_notifications("u")
    assert got == ["first", "second"]
    assert not M.has_pending("u")          # delivered only once
    assert M.pop_notifications("u") == []


def test_alert_subscription_toggle(M):
    assert M.alert_subscribers() == []
    M.set_alerts("u", True)
    assert M.get_alerts("u") and "u" in M.alert_subscribers()
    M.set_alerts("u", False)
    assert not M.get_alerts("u") and M.alert_subscribers() == []


def test_wipe_removes_notifications(M):
    M.add_notification("u", "hi")
    M.wipe_user("u")
    assert not M.has_pending("u")
