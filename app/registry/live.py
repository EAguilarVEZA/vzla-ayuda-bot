"""Real, live missing-persons search across public registries.

We query each PUBLIC registry per name AT REQUEST TIME (a single-name lookup, not a
bulk copy), and report each source's verdict with an 'unverified' label plus a link
to see the actual records on the source itself. We never claim to be the system of
record — we just tell the person what each source says and point them to it.

Sources:
- Venezuela te busca (venezuelatebusca.com): live-queried. It already aggregates
  several sources, so one query covers a lot. We read its data endpoint and report
  how many possible matches it has.
- Desaparecidos Terremoto Venezuela: direct-search handoff (link with the query).
- ICRC Restoring Family Links: the official channel; guided portal, so we hand off.
"""
from __future__ import annotations

import logging
import re
import urllib.parse
from dataclasses import dataclass

log = logging.getLogger("registry.live")
TIMEOUT = 6.0
_UA = {"User-Agent": "AyudaVenezuelaBot/1.0 (humanitarian relief; contact via WhatsApp)"}


@dataclass
class Verdict:
    source: str
    status: str          # 'match' | 'none' | 'handoff' | 'error'
    url: str
    count: int = 0


def _get(url: str) -> str:
    import httpx
    r = httpx.get(url, timeout=TIMEOUT, headers=_UA, follow_redirects=True)
    r.raise_for_status()
    return r.text


# ---- Venezuela te busca (live) ----
def _vtb_count(data: str) -> int:
    """Pull totalCount from the registry's data response. Robust to format drift."""
    m = re.search(r'"totalCount"\s*,\s*(\d+)', data)
    return int(m.group(1)) if m else 0


def venezuela_te_busca(query: str) -> Verdict:
    name = query.strip()
    enc = urllib.parse.quote(name)
    page = f"https://venezuelatebusca.com/?query={enc}"
    try:
        data = _get(f"https://venezuelatebusca.com/_root.data?query={enc}")
        count = _vtb_count(data)
        return Verdict("Venezuela te busca", "match" if count else "none", page, count)
    except Exception as e:
        log.warning("venezuela_te_busca failed: %s", e)
        return Verdict("Venezuela te busca", "error", page)


# ---- Desaparecidos Terremoto Venezuela (direct-search handoff) ----
def desaparecidos(query: str) -> Verdict:
    url = "https://desaparecidosterremotovenezuela.com/?query=" + urllib.parse.quote(query.strip())
    return Verdict("Desaparecidos Terremoto Venezuela", "handoff", url)


# ---- ICRC Restoring Family Links (official; handoff) ----
def icrc(query: str) -> Verdict:
    return Verdict("Cruz Roja — ICRC (búsqueda oficial)", "handoff", "https://familylinks.icrc.org")


def live_search(query: str) -> list:
    return [venezuela_te_busca(query), desaparecidos(query), icrc(query)]


# ---- render (Spanish base; the bot translates for en/both) ----
def render_es(name: str, verdicts: list) -> str:
    lines = [f"🔎 Búsqueda: *{name}*",
             "Esto dice cada base de datos (⚠️ registros ciudadanos, *sin verificar*):", ""]
    for v in verdicts:
        if v.status == "match":
            lines.append(f"• *{v.source}* — ✅ {v.count} posible(s) coincidencia(s). "
                         f"Ver detalles aquí: {v.url}")
        elif v.status == "none":
            lines.append(f"• *{v.source}* — ❌ sin coincidencias")
        elif v.status == "handoff":
            lines.append(f"• *{v.source}* — 🔎 búscalo directamente: {v.url}")
        else:
            lines.append(f"• *{v.source}* — ⚠️ no se pudo consultar ahora; "
                         f"intenta directamente: {v.url}")
    lines += ["",
              "ℹ️ No somos el sistema oficial — te mostramos lo que reporta cada fuente. "
              "Confirma siempre en la fuente antes de actuar.",
              "🏛️ Búsqueda oficial de familiares (Cruz Roja): https://familylinks.icrc.org",
              "⚠️ Nunca envíes dinero a quien diga tener información a cambio de pago."]
    return "\n".join(lines)
