"""Shared, defensive parser that turns a source's raw hit dicts into
PersonRecords. Tolerant of missing/renamed fields so one source's schema quirk
can't crash the pipeline.
"""
from __future__ import annotations

from typing import List

from .models import (
    PersonRecord, STATUS_MISSING, STATUS_SAFE, STATUS_DECEASED, STATUS_UNKNOWN,
)

# Map common source status strings (ES/EN) to our vocabulary.
_STATUS_MAP = {
    "missing": STATUS_MISSING, "desaparecido": STATUS_MISSING,
    "desaparecida": STATUS_MISSING, "buscado": STATUS_MISSING,
    "safe": STATUS_SAFE, "encontrado": STATUS_SAFE, "encontrada": STATUS_SAFE,
    "a salvo": STATUS_SAFE, "localizado": STATUS_SAFE, "found": STATUS_SAFE,
    "fallecido": STATUS_DECEASED, "deceased": STATUS_DECEASED,
    "muerto": STATUS_DECEASED,
}

_NAME_KEYS = ("full_name", "name", "nombre", "nombre_completo")
_AGE_KEYS = ("age", "edad")
_LOC_KEYS = ("location", "ubicacion", "zona", "ciudad", "city")
_STATUS_KEYS = ("status", "estado", "situacion")
_URL_KEYS = ("url", "link", "source_url", "enlace")
_DATE_KEYS = ("reported_at", "fecha", "date", "updated_at")


def _first(d: dict, keys) -> object:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None


def _norm_status(value) -> str:
    if not value:
        return STATUS_UNKNOWN
    return _STATUS_MAP.get(str(value).strip().lower(), STATUS_UNKNOWN)


def _norm_age(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_generic_hits(raw: list, source: str, verified: bool,
                       fallback_url: str) -> List[PersonRecord]:
    out: List[PersonRecord] = []
    for hit in raw or []:
        if not isinstance(hit, dict):
            continue
        name = _first(hit, _NAME_KEYS)
        if not name:
            continue  # never emit a record without a name
        out.append(PersonRecord(
            full_name=str(name).strip(),
            source=source,
            source_url=str(_first(hit, _URL_KEYS) or fallback_url),
            status=_norm_status(_first(hit, _STATUS_KEYS)),
            age=_norm_age(_first(hit, _AGE_KEYS)),
            location=(_first(hit, _LOC_KEYS) or None),
            reported_at=(_first(hit, _DATE_KEYS) or None),
            verified=verified,
            raw=hit,
        ))
    return out
