"""Core bot: bilingual onboarding, vetted info, and the cross-border hero network.

- Language: each user picks es / en / both. Interface strings come from i18n;
  KB content is Spanish and translated on the fly (cached).
- Hero network: 'need' and 'offer' posts stored bilingually so an English
  volunteer in the US and a Spanish speaker in Venezuela can be matched and
  each reads the other in their own language.
"""
import json
import logging
import re
from . import llm, knowledge, matching as M, i18n, menu, analytics, config, trust, partners, places
from .menu import MenuReply, MediaReply

# A standalone "lat,lon" message (optionally prefixed "ubicacion") => a location.
_COORD_RE = re.compile(r"^(?:ubicaci[oó]n|location|loc)?\s*(-?\d{1,2}\.\d+)\s*[, ]\s*(-?\d{1,3}\.\d+)\s*$",
                       re.IGNORECASE)


def _detect_location(body, lat, lon):
    if lat is not None and lon is not None:
        try:
            return float(lat), float(lon)
        except (TypeError, ValueError):
            return None
    m = _COORD_RE.match((body or "").strip())
    if m:
        return float(m.group(1)), float(m.group(2))
    return None

log = logging.getLogger("bot")

POST_LIMIT_PER_DAY = 5   # rate limit: hero-network posts per number per day
_CONTACT_RE = re.compile(r"[+]?\d[\d\s().-]{6,}\d")


def _loads(s):
    """Never let a corrupted session blob crash a reply."""
    try:
        return json.loads(s or "{}")
    except Exception:
        return {}


def _safe_lang(user):
    try:
        return M.get_lang(user) if M.user_exists(user) else "both"
    except Exception:
        return "both"
from .registry import live as registry_live

_kb_en_cache = {}


def _menu(lang, body=None):
    """The main menu as a MenuReply: renders as grouped text everywhere, and as
    a native interactive list when main.py detects it on the Business API.

    `body` (e.g. a 'language set' confirmation) shows above the text menu and is
    used as the list's body text in the native version."""
    text = menu.menu_text(lang)
    if body:
        text = body + "\n\n" + text
    return MenuReply(text, lang=lang, body=body)

NUM_TO_INTENT = {
    "1": "missing_persons", "2": "mark_safe", "3": "shelter", "4": "food",
    "5": "medical", "6": "mental_health", "7": "events", "8": "hero",
    "9": "browse", "10": "how_to_help", "11": "scams",
}

# Deterministic keyword router — runs BEFORE the LLM so the common asks cost
# zero tokens. (Cost optimization; the classifier is the fallback.) Keys are
# substrings matched against the lowercased message, in priority order.
KEYWORD_INTENTS = [
    (("desaparec", "busco a", "buscar a", "missing", "find my"), "missing_persons"),
    (("esta bien", "está bien", "a salvo", "encontr", "mark safe", "is safe"), "mark_safe"),
    (("refugio", "albergue", "shelter", "where to stay", "donde quedar"), "shelter"),
    (("comida", "agua", "hambre", "food", "water"), "food"),
    (("medic", "médic", "hospital", "medicina", "insumo", "supplies", "medical"), "medical"),
    (("psicolog", "emocional", "ansiedad", "mental", "emotional support"), "mental_health"),
    (("evento", "jornada", "event"), "events"),
    (("voluntari", "quiero ayudar", "want to help", "ofrezco", "i can help"), "hero_offer"),
    (("necesito ayuda", "need help", "ayúdenme", "ayudenme"), "hero_need"),
    (("ver solicitud", "browse", "quien necesita", "who needs"), "browse"),
    (("donar", "donate", "donación", "donacion", "como ayudo", "how to help"), "how_to_help"),
    (("estafa", "fraude", "scam", "fraud"), "scams"),
]


def keyword_intent(low):
    """Return an intent if a distinctive keyword matches, else None."""
    for words, intent in KEYWORD_INTENTS:
        if any(w in low for w in words):
            return intent
    return None


def _share(lang):
    return i18n.t(lang, "share").replace("{link}", config.PUBLIC_BOT_LINK)


# ---------- helpers ----------
_CAP_TYPE = {"shelter": "shelter", "food": "food", "medical": "medical"}


def _live_capacity(cat_key, lang):
    """Live availability that partner orgs pushed via the portal API, surfaced
    inside the relevant KB answer. Full sites are hidden."""
    t = _CAP_TYPE.get(cat_key)
    if not t:
        return ""
    rows = [r for r in partners.list_capacity(type_=t, limit=6)
            if r.get("status") != "full"]
    if not rows:
        return ""
    hdr = "📍 " + ("Disponibilidad en vivo (organizaciones):" if lang != "en"
                   else "Live availability (partner orgs):")
    lines = [hdr]
    for r in rows:
        limited = (" — cupo limitado / limited" if r.get("status") == "limited" else "")
        detail = f" — {r['detail']}" if r.get("detail") else ""
        lines.append(f"• {r['name']} — {r.get('location','')}{limited}{detail}")
    return "\n".join(lines)


def _kb_reply(cat_key, lang):
    es = knowledge.render_category(cat_key)
    if lang == "es":
        base = es
    else:
        if cat_key not in _kb_en_cache:
            _kb_en_cache[cat_key] = llm.translate(es, "en")
        en = _kb_en_cache[cat_key]
        base = en if lang == "en" else es + "\n— — —\n" + en
    cap = _live_capacity(cat_key, lang)
    return base + ("\n\n" + cap if cap else "")


def _pick_desc(m, lang):
    if lang == "en":
        return m.get("desc_en") or m.get("desc_es") or ""
    if lang == "both":
        return (m.get("desc_es") or "") + " / " + (m.get("desc_en") or "")
    return m.get("desc_es") or m.get("desc_en") or ""


# ---------- entry ----------
def _notify_match(recipient, data):
    """Queue a 'new match' notice for the other side, in their language."""
    rlang = M.get_lang(recipient)
    desc = _pick_desc({"desc_es": data.get("desc_es"), "desc_en": data.get("desc_en")}, rlang)
    text = (i18n.t(rlang, "notify_match")
            .replace("{cat}", data.get("category", ""))
            .replace("{desc}", desc)
            .replace("{contact}", data.get("contact") or ""))
    M.add_notification(recipient, text)


def handle(user, body, lat=None, lon=None):
    """Public entry. Crash-proof: any unexpected error returns a friendly
    fallback instead of dropping the user's message. Also delivers queued
    notifications (e.g. new matches) when the user isn't mid-flow."""
    try:
        reply = _handle(user, body, lat, lon)
    except Exception:
        log.exception("bot error for user=%s", user)
        return i18n.t(_safe_lang(user), "error_generic")
    try:
        state, _ = M.get_session(user)
        if (not state or state == "lang") and M.has_pending(user):
            pend = M.pop_notifications(user)
            if pend:
                return "\n\n".join(pend) + "\n\n— — —\n" + str(reply)
    except Exception:
        log.exception("notification delivery failed for user=%s", user)
    return reply


def _handle(user, body, lat=None, lon=None):
    text = (body or "").strip()
    low = text.lower()

    # Banned users get a polite stop and go no further.
    if M.is_banned(user):
        lang = M.get_lang(user) if M.user_exists(user) else "both"
        return i18n.t(lang, "banned")

    # Shared location (WhatsApp pin) or typed coordinates -> nearest help.
    loc = _detect_location(body, lat, lon)
    if loc:
        lang = M.get_lang(user) if M.user_exists(user) else "es"
        M.clear_session(user)
        analytics.log_event(user, "nearby", lang=lang)
        es = places.render_nearest_es(loc[0], loc[1])
        return llm.translate(es, "en") if lang == "en" else es

    if low in ("borrar", "delete", "eliminar"):
        M.wipe_user(user)
        return i18n.t("es", "privacy") + "\n" + i18n.t("en", "privacy")

    if low in ("idioma", "language", "lang"):
        M.set_session(user, "lang", "{}")
        return i18n.STR["choose_lang"]["es"]

    # First-time user -> choose language
    if not M.user_exists(user):
        state, _ = M.get_session(user)
        if state != "lang":
            M.set_session(user, "lang", "{}")
            return i18n.STR["choose_lang"]["es"]

    state, scratch = M.get_session(user)

    if state == "lang":
        choice = i18n.LANG_CHOICES.get(low)
        if not choice:
            if low in ("español", "espanol", "es"):
                choice = "es"
            elif low in ("english", "en", "ingles", "inglés"):
                choice = "en"
            elif low in ("ambos", "both", "los dos"):
                choice = "both"
        if not choice:
            return i18n.STR["choose_lang"]["es"]
        M.set_lang(user, choice)
        M.clear_session(user)
        body = i18n.t(choice, "lang_set") + "\n" + i18n.t(choice, "cross_border_nudge")
        return _menu(choice, body=body)

    lang = M.get_lang(user)

    # If mid hero-network flow, keep going — only explicit menu/cancel breaks out.
    # (This must come BEFORE greeting handling so answers like "help" or "yes"
    #  aren't mistaken for the menu keyword.)
    if state and state.startswith("net:"):
        if low in ("menu", "menú", "cancelar", "cancel", "salir", "exit"):
            M.clear_session(user)
            return _menu(lang)
        return _hero_flow(user, text, lang, state, scratch)

    # Mid missing-persons search: next message is the name to look up.
    if state and state.startswith("search:"):
        if low in ("menu", "menú", "cancelar", "cancel", "salir", "exit"):
            M.clear_session(user)
            return _menu(lang)
        return _search_flow(user, text, lang)

    # Trust & safety: report / block flows.
    if state == "report:await":
        M.clear_session(user)
        if low in ("menu", "menú", "cancelar", "cancel"):
            return _menu(lang)
        contact_m = _CONTACT_RE.search(text)
        contact = contact_m.group(0).strip() if contact_m else None
        M.add_report(user, contact, "user_report", text)
        if contact:
            M.suspend_posts_by_contact(contact)
        return i18n.t(lang, "report_done")
    if state == "block:await":
        M.clear_session(user)
        if low in ("menu", "menú", "cancelar", "cancel"):
            return _menu(lang)
        M.add_block(user, text.strip())
        return i18n.t(lang, "block_done")

    if low in ("resuelto", "resolved", "resuelta", "listo"):
        M.resolve_user_posts(user)
        return i18n.t(lang, "resolved_done")
    if low in ("alertas", "alerts", "alerta", "alert"):
        new = not M.get_alerts(user)
        M.set_alerts(user, new)
        return i18n.t(lang, "alerts_on" if new else "alerts_off")

    if low in ("reportar", "report", "denunciar"):
        M.set_session(user, "report:await", "{}")
        return i18n.t(lang, "report_ask")
    if low in ("bloquear", "block"):
        M.set_session(user, "block:await", "{}")
        return i18n.t(lang, "block_ask")

    if low in ("compartir", "share", "invitar", "invite"):
        return _share(lang)

    if low in ("menu", "menú", "inicio", "start", "hola", "hi", "hello",
               "?", "0", "ayuda", "help", "opciones", "options", "info"):
        M.clear_session(user)
        return _menu(lang)

    # Routing, cheapest first: numeric shortcut -> keyword router -> LLM.
    intent = NUM_TO_INTENT.get(low) or keyword_intent(low)
    if not intent:
        intent = llm.classify(text).get("intent", "menu")
        if intent == "need_help":
            intent = "hero_need"
        elif intent == "volunteer":
            intent = "hero_offer"

    # Anonymized analytics (no PII) — powers the dashboard + needs heatmap.
    analytics.log_event(user, intent, lang=lang)
    return _route(user, lang, intent)


def _route(user, lang, intent):
    # Missing persons -> start the live federated registry search.
    if intent == "missing_persons":
        M.set_session(user, "search:name", "{}")
        return i18n.t(lang, "ask_search_name")

    if intent in knowledge.INTENT_TO_CATEGORY:
        reply = _kb_reply(knowledge.INTENT_TO_CATEGORY[intent], lang)
        # For location-based help, invite the user to share their location.
        if intent in ("shelter", "food", "medical", "supplies"):
            reply += "\n\n" + i18n.t(lang, "share_location")
        return reply + "\n\n" + i18n.t(lang, "more_options")

    if intent == "mark_safe":
        return i18n.t(lang, "mark_safe")

    if intent == "browse":
        return _browse(user, lang)

    if intent in ("hero", "hero_need", "hero_offer"):
        data = {}
        if intent == "hero_need":
            data["kind"] = "need"
            M.set_session(user, "net:category", json.dumps(data))
            return i18n.t(lang, "ask_category")
        if intent == "hero_offer":
            data["kind"] = "offer"
            M.set_session(user, "net:category", json.dumps(data))
            return i18n.t(lang, "ask_category")
        M.set_session(user, "net:role", json.dumps(data))
        return i18n.t(lang, "ask_role")

    return _menu(lang)


def _badge(m, lang):
    return "  " + i18n.t(lang, "verified_badge") if m.get("_verified") else ""


def _browse(user, lang):
    offers = M.list_open("offer", 3, viewer=user)
    needs = M.list_open("need", 3, viewer=user)
    if not offers and not needs:
        return i18n.t(lang, "browse_empty")
    lines = [i18n.t(lang, "browse_header")]
    if offers:
        lines.append("\n🦸 " + ("Ofrecen ayuda / Offering help:" if lang != "en" else "Offering help:"))
        for m in offers:
            lines.append(f"• [{m['category']}/{m.get('mode','')}] {_pick_desc(m, lang)} — {m['contact']}{_badge(m, lang)}")
    if needs:
        lines.append("\n🙏 " + ("Necesitan ayuda / Need help:" if lang != "en" else "Need help:"))
        for m in needs:
            lines.append(f"• [{m['category']}/{m.get('mode','')}] {_pick_desc(m, lang)} — {m['contact']}{_badge(m, lang)}")
    lines.append("\n" + i18n.t(lang, "safety_card"))
    return "\n".join(lines)


# ---------- missing-persons federated search ----------
def _parse_search_input(text):
    """Accept 'Name', 'Name, age', or 'Name, age, city' in any order for the
    last two. Returns (name, age, location)."""
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if not parts:
        return "", None, None
    name = parts[0]
    age, location = None, None
    for extra in parts[1:]:
        if extra.isdigit() and age is None:
            age = int(extra)
        elif location is None:
            location = extra
    return name, age, location


def _search_flow(user, text, lang):
    name, age, location = _parse_search_input(text)
    if not name:
        return i18n.t(lang, "ask_search_name")

    # Live, stateless query across the public registries; nothing is persisted.
    verdicts = registry_live.live_search(name)
    es = registry_live.render_es(name, verdicts)
    photos = [p.photo for v in verdicts for p in getattr(v, "people", []) if p.photo]
    M.clear_session(user)

    if lang == "es":
        body = es
    else:
        en = llm.translate(es, "en")
        body = en if lang == "en" else es + "\n— — —\n" + en
    text_out = body + "\n\n" + i18n.t(lang, "more_options")
    # On WhatsApp, attach the found person's photo(s) as inline images.
    return MediaReply(text_out, media=photos) if photos else text_out


# ---------- hero-network state machine ----------
def _hero_flow(user, text, lang, state, scratch):
    data = _loads(scratch)
    low = text.lower()
    step = state.split(":", 1)[1]

    if step == "role":
        if low.startswith(("nece", "need")):
            data["kind"] = "need"
        elif low.startswith(("ayud", "help", "ofre", "volunt")):
            data["kind"] = "offer"
        else:
            return i18n.t(lang, "ask_role")
        M.set_session(user, "net:category", json.dumps(data))
        return i18n.t(lang, "ask_category")

    if step == "category":
        cat = M.canon_category(text)
        if not cat:
            return i18n.t(lang, "ask_category")
        data["category"] = cat
        if cat in M.HIGH_RISK_CATEGORIES:
            M.clear_session(user)
            kb = "shelter" if cat == "alojamiento" else "how_to_help"
            return i18n.t(lang, "high_risk_redirect") + "\n\n" + _kb_reply(kb, lang)
        M.set_session(user, "net:mode", json.dumps(data))
        return i18n.t(lang, "ask_mode")

    if step == "mode":
        if low.startswith(("remot",)):
            data["mode"] = "remoto"
        elif low.startswith(("pres", "inper", "in per", "person")):
            data["mode"] = "presencial"
        else:
            return i18n.t(lang, "ask_mode")
        M.set_session(user, "net:region", json.dumps(data))
        return i18n.t(lang, "ask_region")

    if step == "region":
        if low in ("eeuu", "usa", "us", "estados unidos"):
            data["region"] = "US"
        elif low in ("venezuela", "ve", "vzla"):
            data["region"] = "VE"
        else:
            data["region"] = "other"
        if data.get("mode") == "presencial":
            M.set_session(user, "net:location", json.dumps(data))
            return i18n.t(lang, "ask_location")
        data["location"] = None
        M.set_session(user, "net:desc", json.dumps(data))
        return i18n.t(lang, "ask_desc")

    if step == "location":
        data["location"] = text.strip()
        M.set_session(user, "net:desc", json.dumps(data))
        return i18n.t(lang, "ask_desc")

    if step == "desc":
        original = text.strip()
        # Hard minor protection: never peer-match anything involving a child.
        if trust.detect_minor(original):
            M.clear_session(user)
            return (i18n.t(lang, "minor_redirect") + "\n\n"
                    + i18n.t(lang, "child_orgs"))
        # Safety screen: block scams / sexual / off-platform luring before posting.
        ok, reason = trust.screen(original)
        if not ok:
            M.clear_session(user)
            return i18n.t(lang, "safety_blocked")
        if lang == "en":
            data["desc_en"] = original
            data["desc_es"] = llm.translate(original, "es")
        else:
            data["desc_es"] = original
            data["desc_en"] = llm.translate(original, "en")
        M.set_session(user, "net:contact", json.dumps(data))
        return i18n.t(lang, "ask_contact")

    if step == "contact":
        data["contact"] = text.strip()
        M.set_session(user, "net:consent", json.dumps(data))
        return i18n.t(lang, "ask_consent") + "\n" + i18n.t(lang, "money_warning")

    if step == "consent":
        consent = low.startswith(("s", "y"))  # si / yes
        # Rate limit: cap posts per number per day to blunt spam/abuse.
        if M.count_posts_today(user) >= POST_LIMIT_PER_DAY:
            M.clear_session(user)
            return i18n.t(lang, "rate_limited")
        M.add_post(user, data["kind"], data["category"], data.get("mode"),
                   data.get("region"), data.get("location"),
                   data.get("desc_es"), data.get("desc_en"),
                   data.get("contact"), consent)
        # Anonymized: log the hero-network category + coarse location for the
        # heatmap (never the description or contact).
        analytics.log_event(user, "hero_" + data["kind"], region=data.get("region"),
                            location=data.get("location"), lang=lang)
        M.clear_session(user)
        if not consent:
            return i18n.t(lang, "saved_no_consent")
        matches = M.find_matches(data["kind"], data["category"], data.get("mode"),
                                 data.get("region"), data.get("location"), viewer=user)
        if not matches:
            return (i18n.t(lang, "saved_no_match") + "\n" + i18n.t(lang, "resolve_hint")
                    + "\n" + i18n.t(lang, "privacy"))
        lines = [i18n.t(lang, "matches_header")]
        for m in matches:
            loc = m.get("location") or m.get("region") or ""
            lines.append(f"• {_pick_desc(m, lang)} — {loc} — {m['contact']}{_badge(m, lang)}")
            if m.get("_cross_border"):
                lines.append("  " + i18n.t(lang, "cross_border_tag"))
            # Notify-on-match: tell the OTHER side a new match appeared, in their
            # language, delivered next time they message.
            _notify_match(m["user"], data)
        lines.append("\n" + i18n.t(lang, "safety_card"))
        lines.append(i18n.t(lang, "resolve_hint"))
        return "\n".join(lines)

    M.clear_session(user)
    return _menu(lang)
