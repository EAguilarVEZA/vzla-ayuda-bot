"""Location-aware "nearest help" — share GPS, get the closest places + distance.

A user shares their WhatsApp location (or types coordinates); we return the
nearest shelters / food / water / medical points with the address, how far away,
and a tap-to-open Google Maps directions link.

Data: today this uses a clearly-labeled SAMPLE set of coordinates so the feature
is testable. Real places come from the org portal capacity (each capacity entry
gains a lat/lon, or we geocode its address) — then this same code serves verified
locations. Nothing here is presented as confirmed beyond what the source says.
"""
from __future__ import annotations

import math
import urllib.parse

# SAMPLE places (La Guaira / Vargas coast). Clearly not verified — for testing the
# experience until real org-portal data with coordinates is connected.
SAMPLE = [
    {"type": "shelter", "name": "Refugio Escuela Bolivariana", "address": "Av. Soublette, La Guaira", "lat": 10.6025, "lon": -66.9330},
    {"type": "shelter", "name": "Albergue Polideportivo", "address": "Catia La Mar", "lat": 10.6010, "lon": -67.0180},
    {"type": "food", "name": "Punto de comida Cruz Roja", "address": "Maiquetía, frente a la plaza", "lat": 10.5990, "lon": -66.9720},
    {"type": "food", "name": "Olla solidaria", "address": "Caraballeda", "lat": 10.6110, "lon": -66.8510},
    {"type": "water", "name": "Punto de agua potable", "address": "Maiquetía", "lat": 10.5975, "lon": -66.9750},
    {"type": "medical", "name": "Clínica móvil Caritas", "address": "La Guaira centro", "lat": 10.6040, "lon": -66.9280},
    {"type": "medical", "name": "Hospital de campaña", "address": "Catia La Mar", "lat": 10.6000, "lon": -67.0150},
]

_TYPE_ES = {"shelter": "Refugio", "food": "Comida", "water": "Agua", "medical": "Médico"}
_GROUPS = ["shelter", "food", "water", "medical"]


def haversine_km(a_lat, a_lon, b_lat, b_lon) -> float:
    r = 6371.0
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp = math.radians(b_lat - a_lat)
    dl = math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(h)))


def _fmt_dist(km: float) -> str:
    return f"{int(round(km * 1000))} m" if km < 1 else f"{km:.1f} km"


def maps_link(lat, lon) -> str:
    return "https://www.google.com/maps/dir/?api=1&destination=" + urllib.parse.quote(f"{lat},{lon}")


def nearest(lat, lon, type_=None, n=2, places=None):
    src = places if places is not None else SAMPLE
    items = [p for p in src if (type_ is None or p.get("type") == type_)]
    for p in items:
        p = p  # keep ref
    scored = sorted(items, key=lambda p: haversine_km(lat, lon, p["lat"], p["lon"]))
    out = []
    for p in scored[:n]:
        d = haversine_km(lat, lon, p["lat"], p["lon"])
        out.append({**p, "distance_km": d, "distance": _fmt_dist(d),
                    "maps": maps_link(p["lat"], p["lon"])})
    return out


def render_nearest_es(lat, lon, places=None) -> str:
    lines = ["📍 Lo más cercano a tu ubicación (⚠️ datos de muestra hasta confirmar con aliados):", ""]
    any_found = False
    for g in _GROUPS:
        items = nearest(lat, lon, g, n=2, places=places)
        if not items:
            continue
        any_found = True
        lines.append(f"*{_TYPE_ES[g]}*")
        for it in items:
            lines.append(f"• {it['name']} — {it['address']} — a {it['distance']}")
            lines.append(f"  🗺️ Cómo llegar: {it['maps']}")
        lines.append("")
    if not any_found:
        return "No tengo lugares cargados todavía para tu zona. Escribe MENU para otras opciones."
    lines.append("⚠️ Confirma que el lugar esté abierto antes de ir. En peligro inmediato, "
                 "llama a los servicios de emergencia.")
    return "\n".join(lines)
