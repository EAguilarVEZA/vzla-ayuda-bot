"""Adapter: ICRC 'Restoring Family Links' (authoritative, verified).

ICRC is the official family-reunification channel. We treat its data as verified
and always surface it first. We never scrape it; we link families to its own
search and, when a confirmed query surface exists, query it live.
"""
from __future__ import annotations

from typing import List

from ..base import SourceAdapter
from ..models import PersonRecord, Query
from .._parse import parse_generic_hits


class ICRCAdapter(SourceAdapter):
    name = "ICRC Restoring Family Links"
    verified = True
    search_page = "https://familylinks.icrc.org"

    def _raw_hits(self, query: Query) -> list | None:
        """ICRC RFL is primarily a guided portal rather than an open search API.
        Default behavior is to hand the family the authoritative portal link.
        TODO(edgar): if/when a partner query surface is available, wire it here."""
        return None

    def search(self, query: Query) -> List[PersonRecord]:
        try:
            raw = self._raw_hits(query)
        except Exception:
            raw = None
        if not raw:
            return [self.link_only_result(
                query,
                note="Búsqueda oficial de familiares (Cruz Roja) / official "
                     "family search (Red Cross).",
            )]
        return parse_generic_hits(raw, source=self.name, verified=self.verified,
                                  fallback_url=self.deep_link(query))
