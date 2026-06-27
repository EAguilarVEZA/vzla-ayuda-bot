"""Knowledge base guards: it loads, and no dev placeholders leak to users."""
from app import knowledge


def test_kb_loads_all_categories():
    assert knowledge.CATEGORIES
    for key in ("shelter", "food", "medical", "mental_health", "missing_persons",
                "how_to_help", "scams"):
        assert key in knowledge.CATEGORIES


def test_no_dev_placeholders_render_to_users():
    for key in knowledge.CATEGORIES:
        text = knowledge.render_category(key)
        assert "VERIFICAR" not in text, f"placeholder leaked in '{key}'"
        assert "ACTUALIZAR" not in text


def test_missing_persons_carries_unverified_disclaimer():
    text = knowledge.render_category("missing_persons")
    assert "NO" in text or "no verificad" in text.lower()  # unverified-registry note
