"""Loads the vetted knowledge base and renders Spanish replies from it.

The bot ONLY presents information that lives in resources.yaml. This keeps
answers grounded and prevents the model from inventing shelters, numbers,
or organizations.
"""
import os
import yaml

_KB_PATH = os.path.join(os.path.dirname(__file__), "kb", "resources.yaml")

with open(_KB_PATH, "r", encoding="utf-8") as f:
    KB = yaml.safe_load(f)

CATEGORIES = KB.get("categories", {})
DISCLAIMERS = KB.get("disclaimers", {})

# Maps an intent name to a KB category key.
INTENT_TO_CATEGORY = {
    "missing_persons": "missing_persons",
    "shelter": "shelter",
    "food": "food",
    "medical": "medical",
    "supplies": "supplies",
    "mental_health": "mental_health",
    "events": "events",
    "how_to_help": "how_to_help",
    "scams": "scams",
}


def render_category(category_key: str) -> str:
    """Build a Spanish reply for a category straight from the KB."""
    cat = CATEGORIES.get(category_key)
    if not cat:
        return ""

    lines = [f"*{cat.get('title_es', '')}*"]
    if cat.get("intro_es"):
        lines.append(cat["intro_es"])
    lines.append("")

    # Categories like 'scams' use a tips list instead of resources.
    if cat.get("tips_es"):
        for tip in cat["tips_es"]:
            lines.append(f"• {tip}")
        return "\n".join(lines).strip()

    for r in cat.get("resources", []):
        star = "⭐ " if r.get("authoritative") else ""
        line = f"{star}*{r['name']}*"
        lines.append(line)
        if r.get("desc_es"):
            lines.append(f"  {r['desc_es']}")
        if r.get("url"):
            lines.append(f"  {r['url']}")
        if r.get("note_es"):
            lines.append(f"  ⚠️ {r['note_es']}")
        lines.append("")

    # Append the unverified-registry disclaimer where relevant.
    if category_key == "missing_persons":
        lines.append("⚠️ " + DISCLAIMERS.get("unverified_registry", ""))

    return "\n".join(lines).strip()


def kb_context_for_model() -> str:
    """A compact text dump of the KB for the classifier/grounding prompt."""
    return yaml.safe_dump(CATEGORIES, allow_unicode=True, sort_keys=False)
