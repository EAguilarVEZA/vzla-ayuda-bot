"""Normalized data model for federated registry search.

PersonRecord is the common shape every adapter returns. MergedRecord is what the
resolver produces after deduping across sources — it keeps EVERY source so a
family can verify each one independently.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List


# --- status vocabulary -------------------------------------------------------
STATUS_MISSING = "reported_missing"
STATUS_SAFE = "marked_safe"
STATUS_DECEASED = "reported_deceased"
STATUS_UNKNOWN = "unknown"

# Recency priority when merging conflicting statuses from different sources.
# 'safe' and 'deceased' are stronger signals than a stale 'missing', but the
# resolver still SHOWS every source so the family can confirm for themselves.
_STATUS_RANK = {
    STATUS_SAFE: 3,
    STATUS_DECEASED: 3,
    STATUS_MISSING: 2,
    STATUS_UNKNOWN: 1,
}


@dataclass
class Query:
    """A family member's search. Only `name` is required."""
    name: str
    age: Optional[int] = None
    location: Optional[str] = None


@dataclass
class PersonRecord:
    """A single hit from a single source. `verified` is True ONLY for sources
    that confirm their own data (ICRC); citizen registries are always False."""
    full_name: str
    source: str                       # adapter display name
    source_url: str                   # per-record verify / update link
    status: str = STATUS_UNKNOWN
    age: Optional[int] = None
    location: Optional[str] = None
    reported_at: Optional[str] = None  # ISO date string if the source gives one
    verified: bool = False
    note: Optional[str] = None         # e.g. "search this registry directly"
    raw: dict = field(default_factory=dict)

    @property
    def is_link_only(self) -> bool:
        """True when the adapter could not return structured hits and instead
        hands back the registry's own search page (honest fallback, never faked)."""
        return self.status == STATUS_UNKNOWN and self.note is not None and not self.age


@dataclass
class MergedRecord:
    """One person, after entity resolution across sources."""
    full_name: str
    age: Optional[int]
    location: Optional[str]
    status: str
    sources: List[PersonRecord]       # every contributing source, kept intact

    @property
    def any_verified(self) -> bool:
        return any(s.verified for s in self.sources)

    @property
    def best_reported_at(self) -> Optional[str]:
        dates = [s.reported_at for s in self.sources if s.reported_at]
        return max(dates) if dates else None

    @classmethod
    def from_records(cls, records: List[PersonRecord]) -> "MergedRecord":
        """Build a merged view. Status uses the strongest/most-recent signal,
        but all sources are preserved on the record."""
        # Prefer the most-informative name/age/location across sources.
        full_name = max((r.full_name for r in records), key=len)
        age = next((r.age for r in records if r.age is not None), None)
        location = next((r.location for r in records if r.location), None)
        status = max(
            (r.status for r in records),
            key=lambda s: _STATUS_RANK.get(s, 0),
            default=STATUS_UNKNOWN,
        )
        return cls(full_name=full_name, age=age, location=location,
                   status=status, sources=list(records))
