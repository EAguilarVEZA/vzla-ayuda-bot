"""Render merged search results as a safety-first WhatsApp message.

Every result shows: name/age/location, status WITH a timestamp when known, each
contributing source, an 'unverified' tag on citizen-registry data, and a
verify/update link per source. We always close with the ICRC authoritative
handoff. Spanish is the base language; the bot translates to en/both upstream.
"""
from __future__ import annotations

from typing import List

from .models import (
    MergedRecord, STATUS_MISSING, STATUS_SAFE, STATUS_DECEASED, STATUS_UNKNOWN,
)

_STATUS_ES = {
    STATUS_MISSING: "Reportado/a como desaparecido/a",
    STATUS_SAFE: "Reportado/a a salvo",
    STATUS_DECEASED: "Reportado/a fallecido/a",
    STATUS_UNKNOWN: "Estado no confirmado",
}

_ICRC = "https://familylinks.icrc.org"


def render_results_es(name: str, results: List[MergedRecord]) -> str:
    """Build the Spanish reply. The bot handles en/both translation."""
    header = f"🔎 Resultados para *{name}*:"
    if not results:
        return (header + "\n\nNo encontramos coincidencias en los registros "
                "consultados.\n\n" + _footer_es())

    lines = [header, ""]
    for i, m in enumerate(results, 1):
        lines.extend(_render_one_es(i, m))
        lines.append("")
    lines.append(_footer_es())
    return "\n".join(lines).strip()


def _render_one_es(i: int, m: MergedRecord) -> List[str]:
    bits = [f"*{i}. {m.full_name}*"]
    meta = []
    if m.age is not None:
        meta.append(f"{m.age} años")
    if m.location:
        meta.append(m.location)
    if meta:
        bits.append("   " + " · ".join(meta))

    status = _STATUS_ES.get(m.status, _STATUS_ES[STATUS_UNKNOWN])
    when = f" (act. {m.best_reported_at})" if m.best_reported_at else ""
    bits.append(f"   Estado: {status}{when}")

    # Per-source attributions with verify links and unverified tags.
    for s in m.sources:
        tag = "✓ verificado" if s.verified else "⚠️ sin verificar"
        bits.append(f"   • {s.source} [{tag}]")
        if s.note:
            bits.append(f"     {s.note}")
        bits.append(f"     Verificar/actualizar: {s.source_url}")

    if not m.any_verified:
        bits.append("   ⚠️ Datos de registros ciudadanos, *sin verificar*. "
                    "Confirma antes de actuar.")
    return bits


def _footer_es() -> str:
    return (
        "— — —\n"
        "ℹ️ Esta búsqueda consulta registros públicos en vivo; no guardamos una "
        "copia, así que los estados pueden cambiar. Confirma siempre en la fuente.\n"
        f"🏛️ Búsqueda oficial de familiares (Cruz Roja): {_ICRC}\n"
        "⚠️ Nunca envíes dinero a quien diga tener información a cambio de pago."
    )
