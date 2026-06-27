"""Adapter: 'Desaparecidos Terremoto Venezuela' citizen registry (unverified).

The largest of the citizen registries (60k+ names per the brief). Same contract
and same honesty rule as the others: live query when a surface is confirmed,
otherwise a link-only result. Never fabricate records.
"""
from __future__ import annotations

from typing import List

from ..base import SourceAdapter
from ..models import PersonRecord, Query
from .._parse import parse_generic_hits


class DesaparecidosAdapter(SourceAdapter):
    name = "Desaparecidos Terremoto Venezuela"
    verified = False
    search_page = "https://desaparecidosterremotovenezuela.com/?buscar={q}"

    def _raw_hits(self, query: Query) -> list | None:
        """TODO(edgar): confirm the public query surface, then implement the
        live request here (httpx GET, self.timeout_s) and return JSON hits."""
        return None

    def search(self, query: Query) -> List[PersonRecord]:
        try:
            raw = self._raw_hits(query)
        except Exception:
            raw = None
        if not raw:
            return [self.link_only_result(
                query,
                note="Registro más grande; búsqueda directa recomendada / "
                     "largest registry; search it directly.",
            )]
        return parse_generic_hits(raw, source=self.name, verified=self.verified,
                                  fallback_url=self.deep_link(query))
