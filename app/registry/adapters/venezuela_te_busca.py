"""Adapter: 'Venezuela Te Busca' citizen registry (unverified).

STATUS: query surface not yet confirmed. Until Edgar confirms the public search
endpoint (see DEVELOPMENT_PLAN.md 1b), this adapter returns the registry's own
search page as a link-only result — honest, never fabricated. Wire the real
request inside `_raw_hits` and flip nothing else.
"""
from __future__ import annotations

from typing import List

from ..base import SourceAdapter
from ..models import PersonRecord, Query
from .._parse import parse_generic_hits


class VenezuelaTeBuscaAdapter(SourceAdapter):
    name = "Venezuela Te Busca"
    verified = False
    # Public-facing search page. {q} is url-encoded before substitution.
    search_page = "https://venezuelatebusca.com/buscar?q={q}"

    def _raw_hits(self, query: Query) -> list | None:
        """Return a list of raw source dicts, or None if no query surface is
        wired / reachable. Keep this the ONLY place that touches the network so
        the rest of the pipeline stays pure and testable.

        TODO(edgar): confirm endpoint + params, then implement the live request
        here (httpx GET with self.timeout_s) and return response JSON hits.
        """
        return None

    def search(self, query: Query) -> List[PersonRecord]:
        try:
            raw = self._raw_hits(query)
        except Exception:
            raw = None
        if not raw:
            return [self.link_only_result(
                query,
                note="Abre este registro y busca directamente / open this "
                     "registry and search directly.",
            )]
        return parse_generic_hits(raw, source=self.name, verified=self.verified,
                                  fallback_url=self.deep_link(query))
