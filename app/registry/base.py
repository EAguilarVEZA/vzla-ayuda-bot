"""Adapter contract for a missing-persons source.

Every source (citizen registry or ICRC) implements SourceAdapter. Adapters are
read-only and live: they QUERY at request time and never store a copy.

Honesty rule: if a source has no machine-readable query surface (or it can't be
reached right now), the adapter returns a single LINK-ONLY record pointing at the
registry's own search page. It must NEVER fabricate person records.
"""
from __future__ import annotations

import abc
from typing import List
from urllib.parse import quote_plus

from .models import PersonRecord, Query, STATUS_UNKNOWN


class SourceAdapter(abc.ABC):
    name: str = "source"
    verified: bool = False        # True only for sources that confirm their own data
    timeout_s: float = 4.0        # never hang a WhatsApp reply on a slow registry
    search_page: str = ""         # human deep-link search URL; {q} is url-encoded query

    @abc.abstractmethod
    def search(self, query: Query) -> List[PersonRecord]:
        """Return structured hits for the query, or [] if none.

        Implementations should catch their own network errors and degrade to
        `link_only_result()` rather than raising; the service layer also guards
        against exceptions as a backstop.
        """
        raise NotImplementedError

    # -- helpers -------------------------------------------------------------
    def deep_link(self, query: Query) -> str:
        if "{q}" in self.search_page:
            return self.search_page.replace("{q}", quote_plus(query.name))
        return self.search_page

    def link_only_result(self, query: Query, note: str) -> PersonRecord:
        """The honest fallback: hand back the registry's search page so the
        family can look directly. Never presented as a confirmed person."""
        return PersonRecord(
            full_name=query.name,
            source=self.name,
            source_url=self.deep_link(query),
            status=STATUS_UNKNOWN,
            verified=self.verified,
            note=note,
        )
