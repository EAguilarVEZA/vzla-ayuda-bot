"""Anthropic/Claude wrappers: intent classification + two-way translation.

Cost-optimized:
- Defaults to Haiku (config.BOT_MODEL).
- The classifier's long system prompt is marked for *prompt caching* so repeated
  calls bill cached input at ~10%.
- Every call's token usage is recorded (analytics.record_llm_usage) so the
  dashboard cost panel shows measured spend, not just a model.
Note: most traffic never reaches here — the numeric menu + keyword router in
bot.py handle the common asks with zero tokens; this is the fallback.
"""
import json
from anthropic import Anthropic
from . import config, analytics

_client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

INTENTS = [
    "missing_persons", "shelter", "food", "medical", "supplies",
    "mental_health", "events", "how_to_help", "scams",
    "need_help",   # quiere/necesita ayuda  -> hero network (role=need)
    "volunteer",   # quiere ayudar/voluntario -> hero network (role=offer)
    "browse",      # ver solicitudes de la red
    "mark_safe", "set_language", "menu", "other",
]

_CLASSIFY_SYS = f"""Eres el clasificador de un asistente humanitario por WhatsApp
para el terremoto de Venezuela, bilingüe (español/inglés). Devuelve SOLO un JSON:

{{"intent":"<{", ".join(INTENTS)}>","category":null,"location":null,"language":"es|en"}}

Reglas:
- "volunteer" si la persona quiere AYUDAR / ofrecerse / ser voluntario.
- "need_help" si NECESITA ayuda y quiere que la conecten.
- "browse" si quiere VER solicitudes o quién necesita ayuda.
- "missing_persons" si busca/reporta a un ser querido.
- "mark_safe" si alguien está bien / fue encontrado.
- "set_language" si pide cambiar idioma.
- "menu" para saludos o pedir opciones. Si no encaja: "other".
Solo el JSON."""


def _usage(resp):
    """Pull token counts off a response, tolerating SDK shape differences."""
    u = getattr(resp, "usage", None)
    if not u:
        return 0, 0, 0
    cached = getattr(u, "cache_read_input_tokens", 0) or 0
    return (getattr(u, "input_tokens", 0) or 0,
            getattr(u, "output_tokens", 0) or 0, cached)


def classify(message: str) -> dict:
    try:
        resp = _client.messages.create(
            model=config.BOT_MODEL, max_tokens=200,
            # cache_control marks this big system block for prompt caching.
            system=[{"type": "text", "text": _CLASSIFY_SYS,
                     "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": message}],
        )
        in_t, out_t, cached = _usage(resp)
        analytics.record_llm_usage("classify", config.BOT_MODEL, in_t, out_t, cached)
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        text = text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        if data.get("intent") not in INTENTS:
            data["intent"] = "other"
        return data
    except Exception:
        return {"intent": "menu", "category": None, "location": None, "language": "es"}


_LANG_NAME = {"en": "English", "es": "Spanish"}


def translate(text: str, target: str) -> str:
    """Translate text to target ('en'/'es'). Falls back to original on error."""
    if not text or not text.strip():
        return text
    try:
        resp = _client.messages.create(
            model=config.BOT_MODEL, max_tokens=800,
            system=(f"Translate the user's message to {_LANG_NAME.get(target,'English')}. "
                    "Preserve URLs, phone numbers, names, emojis and line breaks. "
                    "Output ONLY the translation."),
            messages=[{"role": "user", "content": text}],
        )
        in_t, out_t, cached = _usage(resp)
        analytics.record_llm_usage("translate", config.BOT_MODEL, in_t, out_t, cached)
        return "".join(b.text for b in resp.content if b.type == "text").strip() or text
    except Exception:
        return text
