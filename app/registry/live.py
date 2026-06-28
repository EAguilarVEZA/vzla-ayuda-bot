"""Real, live missing-persons search across public registries.

We query each PUBLIC registry per name AT REQUEST TIME (a single-name lookup, not a
bulk copy), and report what each source actually says — full record details and a
photo when available — with an 'unverified' label and a link back to the source.
We never claim to be the system of record; we tell the person what each source
reports and point them to it.

Sources:
- Venezuela te busca (venezuelatebusca.com): live-queried with real record details.
  It already aggregates several sources, so one query covers a lot.
- Desaparecidos Terremoto Venezuela: direct-search handoff (link with the query).
- ICRC Restoring Family Links: official channel; guided portal, so we hand off.
"""
from __future__ import annotations

import json
import logging
import re
import urllib.parse
from dataclasses import dataclass, field

log = logging.getLogger("registry.live")
TIMEOUT = 6.0
_UA = {"User-Agent": "AyudaVenezuelaBot/1.0 (humanitarian relief)"}
_VTB = "https://venezuelatebusca.com"

_GENDER_ES = {"female": "Femenino", "male": "Masculino"}
# Public person fields we surface. We deliberately DO NOT surface reporter
# phone/email (PII of the person who filed the report).
_SAFE_FIELDS = ("firstName", "lastName", "age", "gender", "lastSeen",
                "description", "status", "photoUrl")


@dataclass
class Person:
    name: str
    age: object = None
    gender: str = None
    last_seen: str = None
    status: str = None
    description: str = None
    photo: str = None


@dataclass
class Verdict:
    source: str
    status: str            # 'match' | 'none' | 'handoff' | 'error'
    url: str
    count: int = 0
    people: list = field(default_factory=list)


def _get(url: str) -> str:
    import httpx
    r = httpx.get(url, timeout=TIMEOUT, headers=_UA, follow_redirects=True)
    r.raise_for_status()
    return r.text


# ---- turbo-stream decoder (Remix single-fetch format) ----
def _decode(text: str):
    arr = json.loads(text)
    memo = {}

    def resolve(idx):
        if not isinstance(idx, int) or idx < 0:
            return None
        if idx in memo:
            return memo[idx]
        v = arr[idx]
        if isinstance(v, dict):
            out = {}
            memo[idx] = out
            for k, vi in v.items():
                key = arr[int(k.lstrip("_"))]
                out[key] = resolve(vi)
            return out
        if isinstance(v, list):
            out = []
            memo[idx] = out
            out.extend(resolve(i) for i in v)
            return out
        memo[idx] = v
        return v

    return resolve(0)


def _clean_name(first: str, last: str) -> str:
    """Registry records sometimes repeat the name across firstName/lastName
    (e.g. first='Jose Bolivar', last='Jose' -> 'Jose Bolivar Jose'). De-dup the
    tokens, preserving order, so the displayed name reads cleanly."""
    raw = ((first or "").strip() + " " + (last or "").strip()).strip()
    seen, out = set(), []
    for tok in raw.split():
        k = tok.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(tok)
    return " ".join(out) or "—"


def _vtb_count(text: str) -> int:
    """Robust fallback: pull totalCount even if full decoding fails."""
    m = re.search(r'"totalCount"\s*,\s*(\d+)', text)
    return int(m.group(1)) if m else 0


def _persons_and_count(text: str):
    """Return (people, total). Falls back to a regex count if decoding fails."""
    count = _vtb_count(text)
    people = []
    try:
        decoded = _decode(text)
        data = None
        for v in (decoded or {}).values():
            if isinstance(v, dict) and isinstance(v.get("data"), dict) \
                    and "persons" in v["data"]:
                data = v["data"]
                break
        if data:
            count = data.get("totalCount", count) or count
            for p in (data.get("persons") or [])[:3]:
                if not isinstance(p, dict):
                    continue
                first = (p.get("firstName") or "").strip()
                last = (p.get("lastName") or "").strip()
                photo = p.get("photoUrl")
                if photo and not photo.startswith("http"):
                    photo = _VTB + "/" + photo.lstrip("/")
                people.append(Person(
                    name=_clean_name(first, last),
                    age=p.get("age"), gender=p.get("gender"),
                    last_seen=p.get("lastSeen"), status=p.get("status"),
                    description=p.get("description"), photo=photo))
    except Exception as e:
        log.warning("vtb decode failed: %s", e)
    return people, count


def venezuela_te_busca(query: str) -> Verdict:
    enc = urllib.parse.quote(query.strip())
    page = f"{_VTB}/?query={enc}"
    try:
        people, count = _persons_and_count(_get(f"{_VTB}/_root.data?query={enc}"))
        return Verdict("Venezuela te busca", "match" if count else "none",
                       page, count, people)
    except Exception as e:
        log.warning("venezuela_te_busca failed: %s", e)
        return Verdict("Venezuela te busca", "error", page)


def desaparecidos(query: str) -> Verdict:
    url = "https://desaparecidosterremotovenezuela.com/?query=" + urllib.parse.quote(query.strip())
    return Verdict("Desaparecidos Terremoto Venezuela", "handoff", url)


def icrc(query: str) -> Verdict:
    return Verdict("Cruz Roja — ICRC (búsqueda oficial)", "handoff",
                   "https://familylinks.icrc.org")


def live_search(query: str) -> list:
    return [venezuela_te_busca(query), desaparecidos(query), icrc(query)]


# ---- render (Spanish base; the bot translates for en/both) ----
def _status_es(s):
    if s in ("found", "located"):
        return "✅ Reportado/a como LOCALIZADO/A"
    if s == "missing":
        return "Reportado/a como desaparecido/a (sigue sin localizar)"
    return s or "Estado no indicado"


def _person_block(i, p: Person):
    bits = [f"{i}. *{p.name}*"]
    meta = []
    if p.age not in (None, ""):
        meta.append(f"{p.age} años")
    if p.gender:
        meta.append(_GENDER_ES.get(p.gender, p.gender))
    if p.last_seen:
        meta.append(p.last_seen)
    if meta:
        bits.append("   " + " · ".join(meta))
    bits.append("   Estado: " + _status_es(p.status))
    if p.description:
        bits.append("   📝 " + p.description)
    if p.photo:
        bits.append("   📷 Foto: " + p.photo)
    return "\n".join(bits)


def render_es(name: str, verdicts: list) -> str:
    lines = [f"🔎 Búsqueda: *{name}*  (⚠️ registros ciudadanos, *sin verificar*)", ""]
    for v in verdicts:
        if v.status == "match":
            lines.append(f"*{v.source}* — ✅ encontramos {v.count} registro(s) con ese nombre:")
            for i, p in enumerate(v.people, 1):
                lines.append(_person_block(i, p))
            if v.count > len(v.people):
                lines.append(f"   …y {v.count - len(v.people)} más.")
            lines.append(f"👉 Ver todos en la fuente: {v.url}")
        elif v.status == "none":
            lines.append(f"*{v.source}* — ❌ no encontramos a nadie con ese nombre.")
        elif v.status == "handoff":
            lines.append(f"*{v.source}* — 🔎 búscalo directamente: {v.url}")
        else:
            lines.append(f"*{v.source}* — ⚠️ no se pudo consultar ahora; intenta directamente: {v.url}")
        lines.append("")
    # If you found them: offer it as its own action. Typing ENCONTRÉ starts a
    # short guided flow that marks the person located and prepares an update for
    # every registry — instead of dumping raw links here.
    lines.append("🟢 *¿La encontraste?* Escribe *ENCONTRÉ* y te guío para marcarla "
                 "como LOCALIZADA y preparar el aviso a los 3 registros.")
    lines.append("")
    lines += ["ℹ️ No somos el sistema oficial — te mostramos lo que reporta cada fuente. "
              "Confirma siempre en la fuente antes de actuar.",
              "🏛️ Búsqueda oficial de familiares (Cruz Roja): https://familylinks.icrc.org",
              "⚠️ Nunca envíes dinero a quien diga tener información a cambio de pago."]
    return "\n".join(lines)
