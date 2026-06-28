"""Live nearby-places discovery from GPS — OpenStreetMap (Overpass) + partner data.

Given a user's coordinates we query OpenStreetMap for REAL facilities near them
(hospitals, clinics, pharmacies, shelters, community centres, churches, markets)
and return name, address, phone, how far away, and a tap-to-open directions link.

Honesty guardrails:
- OSM is real map data but NOT a live "open right now" feed, so every result is
  labelled "confirma que esté abierto" (confirm it's open before going).
- Places that verified partner orgs pushed via the portal are shown FIRST and
  marked verified.
- Nothing here is presented as official or guaranteed.

Network: the bot queries a public Overpass endpoint at request time (same pattern
as the missing-persons registry). Failures degrade gracefully to partner data +
the vetted national orgs, never a crash.
"""
from __future__ import annotations

import logging

from .places import haversine_km, _fmt_dist, maps_link

log = logging.getLogger("geo")
TIMEOUT = 8.0
_UA = {"User-Agent": "AyudaVenezuelaBot/1.0 (humanitarian relief)"}
_OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]

# Category -> the OSM amenity/shop tags we look for, with a friendly label + icon.
_CATS = {
    "shelter": [
        ("amenity", "shelter", "Refugio", "🏠"),
        ("amenity", "social_facility", "Centro de apoyo", "🏠"),
        ("amenity", "community_centre", "Centro comunitario", "🏠"),
    ],
    "food": [
        ("amenity", "marketplace", "Mercado", "🍲"),
        ("amenity", "community_centre", "Centro comunitario", "🍲"),
        ("amenity", "social_facility", "Centro de apoyo", "🍲"),
        ("shop", "supermarket", "Supermercado", "🛒"),
    ],
    "medical": [
        ("amenity", "hospital", "Hospital", "🏥"),
        ("amenity", "clinic", "Clínica", "🏥"),
        ("amenity", "doctors", "Consultorio", "🩺"),
        ("amenity", "pharmacy", "Farmacia", "💊"),
    ],
    "mental_health": [
        ("amenity", "place_of_worship", "Iglesia / templo", "⛪"),
        ("amenity", "social_facility", "Centro de apoyo", "🤝"),
    ],
}
# When no category is given (a bare location), show the most life-critical mix.
_COMBINED = ["medical", "shelter", "food"]

# Map our categories to partner-portal capacity types (verified orgs).
_CAP_TYPE = {"shelter": "shelter", "food": "food", "medical": "medical"}


def _overpass_query(lat, lon, filters, radius):
    parts = []
    for tag, val, _lbl, _icon in filters:
        for kind in ("node", "way"):
            parts.append(f'{kind}(around:{radius},{lat},{lon})["{tag}"="{val}"];')
    return f"[out:json][timeout:20];({''.join(parts)});out center 40;"


def _fetch_overpass(query):
    import httpx
    for url in _OVERPASS:
        try:
            r = httpx.post(url, data={"data": query}, timeout=TIMEOUT, headers=_UA)
            r.raise_for_status()
            return r.json().get("elements", [])
        except Exception as e:  # try the next mirror
            log.warning("overpass %s failed: %s", url, e)
    return []


def _addr(tags):
    street = tags.get("addr:street") or tags.get("addr:place")
    num = tags.get("addr:housenumber")
    city = tags.get("addr:city")
    if street and num:
        base = f"{street} {num}"
    elif street:
        base = street
    else:
        base = tags.get("addr:full") or ""
    if city and city not in base:
        base = (base + ", " + city).strip(", ")
    return base


def _phone(tags):
    return (tags.get("phone") or tags.get("contact:phone")
            or tags.get("contact:mobile") or "")


def _email(tags):
    return tags.get("email") or tags.get("contact:email") or ""


def _label(tags, filters):
    for tag, val, lbl, icon in filters:
        if tags.get(tag) == val:
            return lbl, icon
    return "Lugar", "📍"


def nearby_osm(lat, lon, category, radius=6000, n=6):
    """Real nearby places from OpenStreetMap, nearest first. Best-effort."""
    filters = _CATS.get(category)
    if not filters:
        return []
    els = _fetch_overpass(_overpass_query(lat, lon, filters, radius))
    out = []
    seen = set()
    for el in els:
        tags = el.get("tags") or {}
        name = tags.get("name")
        if not name:
            continue
        plat = el.get("lat") or (el.get("center") or {}).get("lat")
        plon = el.get("lon") or (el.get("center") or {}).get("lon")
        if plat is None or plon is None:
            continue
        key = name.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        lbl, icon = _label(tags, filters)
        d = haversine_km(lat, lon, plat, plon)
        out.append({
            "name": name.strip(), "label": lbl, "icon": icon,
            "address": _addr(tags), "phone": _phone(tags), "email": _email(tags),
            "distance_km": d, "distance": _fmt_dist(d),
            "maps": maps_link(plat, plon),
        })
    out.sort(key=lambda p: p["distance_km"])
    return out[:n]


def _partner_block(category, lat, lon):
    """Verified org capacity for this category, shown first. Best-effort."""
    t = _CAP_TYPE.get(category)
    if not t:
        return []
    try:
        from . import partners
        rows = [r for r in partners.list_capacity(type_=t, limit=8)
                if r.get("status") != "full"]
    except Exception:
        return []
    return rows


def _emit_place(lines, p):
    head = f"{p['icon']} *{p['name']}* ({p['label']}) — a {p['distance']}"
    lines.append(head)
    if p.get("address"):
        lines.append(f"   📍 {p['address']}")
    if p.get("phone"):
        lines.append(f"   📞 {p['phone']}")
    if p.get("email"):
        lines.append(f"   ✉️ {p['email']}")
    lines.append(f"   🗺️ Cómo llegar: {p['maps']}")


_TITLE = {
    "shelter": "🏠 Refugios y centros cerca de ti",
    "food": "🍲 Comida, mercados y centros cerca de ti",
    "medical": "🏥 Atención médica cerca de ti (hospitales, clínicas, farmacias)",
    "mental_health": "🤝 Apoyo cerca de ti (iglesias y centros de ayuda)",
    None: "📍 Ayuda cerca de ti",
}


def render_nearby_es(lat, lon, category=None) -> str:
    cats = [category] if category else _COMBINED
    title = _TITLE.get(category, _TITLE[None])
    lines = [title, "(⚠️ confirma por teléfono que esté abierto antes de ir)", ""]
    found_any = False

    # 1) Verified partner places first (only for shelter/food/medical).
    for cat in cats:
        rows = _partner_block(cat, lat, lon)
        if rows:
            found_any = True
            lines.append("✅ *Verificado por aliados:*")
            for r in rows[:4]:
                extra = f" — {r['detail']}" if r.get("detail") else ""
                loc = f" ({r['location']})" if r.get("location") else ""
                lines.append(f"   • {r['name']}{loc}{extra}")
            lines.append("")

    # 2) Live OpenStreetMap places, nearest first.
    for cat in cats:
        places = nearby_osm(lat, lon, cat, n=6 if category else 4)
        if not places:
            continue
        found_any = True
        if not category:               # combined view: label each group
            lines.append(f"*{_TITLE.get(cat, '').lstrip('🏥🏠🍲🤝📍 ').strip()}*")
        for p in places:
            _emit_place(lines, p)
        lines.append("")

    if not found_any:
        return ("No encontré lugares cargados para tu zona todavía. "
                "Escribe MENU y elige la opción que necesitas; también puedes "
                "llamar a los servicios de emergencia locales si es urgente.")

    if category == "medical":
        lines.append("🚑 Si es una *emergencia de vida o muerte*, llama ya a los "
                     "servicios de emergencia locales antes de trasladarte.")
    lines.append("ℹ️ Datos de OpenStreetMap y aliados — pueden estar desactualizados. "
                 "Confirma siempre antes de ir.")
    return "\n".join(lines)
