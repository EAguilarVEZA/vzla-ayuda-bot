"""Tests for the single-source menu: text fallback + interactive list payload."""
from app import menu
from app.menu import MenuReply


def test_text_menu_has_sections_and_all_numbers():
    for lang in ("es", "en"):
        t = menu.menu_text(lang)
        for n in range(1, 12):                 # all 11 actions in the text menu
            assert f" {n} " in t or t.endswith(f" {n}") or f"\n  {n} " in t
        assert ("Find" in t) or ("Buscar" in t)


def test_both_includes_two_languages():
    t = menu.menu_text("both")
    assert "Buscar" in t and "Find" in t


def test_menu_intro_advertises_cross_border_bridge():
    # The bilingual-bridge line must be visible in the menu intro (discoverability).
    assert "traduzco" in menu.menu_text("es").lower()
    assert "translate" in menu.menu_text("en").lower()


def test_interactive_payload_within_whatsapp_limits():
    p = menu.interactive_payload("es")
    assert p["type"] == "list"
    sections = p["action"]["sections"]
    rows = [r for s in sections for r in s["rows"]]
    # WhatsApp hard cap: 10 rows total.
    assert len(rows) <= 10
    assert len(rows) == menu.total_quick_rows()
    # ids are the router numbers, so a tapped row routes like typing the number.
    for r in rows:
        assert r["id"].isdigit() and 1 <= int(r["id"]) <= 11
        assert len(r["title"]) <= 24
        assert len(r["description"]) <= 72
    for s in sections:
        assert len(s["title"]) <= 24
    assert 0 < len(p["action"]["button"]) <= 20


def test_interactive_body_uses_custom_body():
    p = menu.interactive_payload("en", body="Language set to English.")
    assert p["body"]["text"] == "Language set to English."


def test_menureply_is_a_string_with_metadata():
    m = MenuReply("hello", lang="en", body="hi")
    assert isinstance(m, str)
    assert m == "hello"
    assert m.lang == "en" and m.body == "hi"
    # concatenation degrades to a plain str (mixed messages send as text)
    assert not isinstance(m + " world", MenuReply)
