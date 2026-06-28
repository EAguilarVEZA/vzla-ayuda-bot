"""Single source of truth for the main menu.

Renders two ways from ONE definition:
- menu_text(lang)        -> grouped, numbered text menu (works on SMS + the
                            Twilio WhatsApp sandbox today).
- interactive_payload()  -> a WhatsApp interactive *list* message (native
                            scrollable picker) for when we're on the Business API.

Row ids are the same numbers the keyword router already understands ("1".."11"),
so a tapped list row arrives as Body="3" and routes exactly like typing "3".

MenuReply is a str subclass: every existing call site can treat it as the text
menu, while main.py can detect it (isinstance) and upgrade to the native list.
"""
from __future__ import annotations

# WhatsApp interactive lists allow at most 10 rows total. We surface the 10 most
# important actions in the native list; the text fallback still lists all 11.
# Each row: id (== router number), bilingual title/desc, and `quick` = show in
# the native list.
SECTIONS = [
    {"key": "find",
     "title": {"es": "Buscar y avisar", "en": "Find & reassure"},
     "rows": [
         {"id": "1", "quick": True,
          "title": {"es": "Buscar a una persona", "en": "Search for a person"},
          "desc": {"es": "Consulta los registros en vivo", "en": "Query registries live"}},
         {"id": "2", "quick": True,
          "title": {"es": "Avisar que está bien", "en": "Mark someone safe"},
          "desc": {"es": "Actualiza su estado", "en": "Update their status"}},
     ]},
    {"key": "help",
     "title": {"es": "Recibir ayuda", "en": "Get help"},
     "rows": [
         {"id": "3", "quick": True,
          "title": {"es": "Refugio", "en": "Shelter"},
          "desc": {"es": "Lugares verificados", "en": "Verified places to stay"}},
         {"id": "4", "quick": True,
          "title": {"es": "Comida y agua", "en": "Food & water"},
          "desc": {"es": "Puntos de distribución", "en": "Distribution points"}},
         {"id": "5", "quick": True,
          "title": {"es": "Médico / insumos", "en": "Medical / supplies"},
          "desc": {"es": "Atención y suministros", "en": "Care and supplies"}},
         {"id": "6", "quick": True,
          "title": {"es": "Apoyo emocional", "en": "Emotional support"},
          "desc": {"es": "Líneas de ayuda", "en": "Support lines"}},
         {"id": "7", "quick": False,
          "title": {"es": "Eventos cerca", "en": "Local events"},
          "desc": {"es": "Jornadas de ayuda", "en": "Help events nearby"}},
     ]},
    {"key": "hero",
     "title": {"es": "Red de héroes", "en": "Hero network"},
     "rows": [
         {"id": "8", "quick": True,
          "title": {"es": "Necesito ayuda", "en": "I need help"},
          "desc": {"es": "Publica tu solicitud", "en": "Post your request"}},
         {"id": "9", "quick": True,
          "title": {"es": "Ofrezco ayuda", "en": "I provide help"},
          "desc": {"es": "Ofrécete como héroe", "en": "Volunteer as a hero"}},
         {"id": "10", "quick": True,
          "title": {"es": "Ver el tablero", "en": "See the board"},
          "desc": {"es": "Solicitudes y ofertas", "en": "Requests and offers"}},
     ]},
    {"key": "safe",
     "title": {"es": "Dar y cuidarte", "en": "Give & stay safe"},
     "rows": [
         {"id": "11", "quick": True,
          "title": {"es": "Donar seguro", "en": "Donate safely"},
          "desc": {"es": "Organizaciones verificadas", "en": "Vetted organizations"}},
         {"id": "12", "quick": False,
          "title": {"es": "Verificar estafa", "en": "Check a scam"},
          "desc": {"es": "Detecta fraudes", "en": "Spot fraud"}},
     ]},
]

_HEADERS = {
    "intro": {
        "es": ("🇻🇪 *Ayuda Venezuela* — responde con un número o escribe lo que necesitas.\n"
               "🌎 Escríbeme en tu idioma: te conecto con alguien en EE.UU. o en Venezuela y traduzco entre los dos."),
        "en": ("🇻🇪 *Ayuda Venezuela* — reply with a number or tell me what you need.\n"
               "🌎 Message me in your language: I'll connect you with someone in the US or Venezuela and translate between you."),
    },
    "footer": {
        "es": "COMPARTIR · CALIFICAR a un héroe · REPORTAR · ALERTAS · IDIOMA · BORRAR.",
        "en": "SHARE · RATE a hero · REPORT · ALERTS · LANGUAGE · DELETE.",
    },
    "button": {"es": "Ver opciones", "en": "See options"},
    "title": {"es": "Ayuda Venezuela", "en": "Ayuda Venezuela"},
    "pick": {"es": "Elige una opción o escribe lo que necesitas.",
             "en": "Pick an option or just tell me what you need."},
}

# WhatsApp field length caps (defensive truncation).
_MAX_ROW_TITLE = 24
_MAX_ROW_DESC = 72
_MAX_SECTION_TITLE = 24
_MAX_BUTTON = 20
_MAX_BODY = 1024


def _L(d, lang):
    """Pick a language string; 'both' falls back to Spanish for compact fields."""
    return d.get("es" if lang in ("es", "both") else "en", d.get("es", ""))


def _trunc(s, n):
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


class MenuReply(str):
    """The text menu, plus metadata so main.py can render the native list."""
    def __new__(cls, text, lang="es", body=None):
        obj = super().__new__(cls, text)
        obj.lang = lang
        obj.body = body
        return obj


class MediaReply(str):
    """A text reply that also carries image URLs. On WhatsApp the webhook attaches
    them so e.g. a missing person's photo shows inline; on SMS/the simulator the
    text (which still includes the photo links) is shown as-is."""
    def __new__(cls, text, media=None):
        obj = super().__new__(cls, text)
        obj.media = list(media or [])[:5]   # WhatsApp caps media per message
        return obj


def _menu_text_one(lang):
    lines = [_HEADERS["intro"][lang], ""]
    for sec in SECTIONS:
        lines.append("*" + sec["title"][lang] + "*")
        for r in sec["rows"]:
            lines.append(f"  {r['id']} {r['title'][lang]}")
        lines.append("")
    lines.append(_HEADERS["footer"][lang])
    return "\n".join(lines).strip()


def menu_text(lang="es"):
    """Grouped, numbered text menu (SMS + sandbox fallback)."""
    if lang == "both":
        return _menu_text_one("es") + "\n— — —\n" + _menu_text_one("en")
    return _menu_text_one(lang)


def interactive_payload(lang="es", body=None):
    """WhatsApp Cloud-API interactive *list* JSON (the canonical shape; Twilio
    Content variables map onto the same fields). Only `quick` rows are included
    so we stay within WhatsApp's 10-row limit."""
    sections = []
    for sec in SECTIONS:
        rows = [
            {
                "id": r["id"],
                "title": _trunc(_L(r["title"], lang), _MAX_ROW_TITLE),
                "description": _trunc(_L(r["desc"], lang), _MAX_ROW_DESC),
            }
            for r in sec["rows"] if r.get("quick")
        ]
        if rows:
            sections.append({
                "title": _trunc(_L(sec["title"], lang), _MAX_SECTION_TITLE),
                "rows": rows,
            })
    body_text = body or _L(_HEADERS["pick"], lang)
    return {
        "type": "list",
        "header": {"type": "text", "text": _L(_HEADERS["title"], lang)},
        "body": {"text": _trunc(body_text, _MAX_BODY)},
        "footer": {"text": _L(_HEADERS["footer"], lang)},
        "action": {
            "button": _trunc(_L(_HEADERS["button"], lang), _MAX_BUTTON),
            "sections": sections,
        },
    }


def total_quick_rows():
    return sum(1 for sec in SECTIONS for r in sec["rows"] if r.get("quick"))
