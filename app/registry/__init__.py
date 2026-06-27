"""Federated missing-persons search.

Design (see docs/DEVELOPMENT_PLAN.md, Phase 1):
- We QUERY public registries + ICRC live, at request time. We never bulk-scrape
  or rehost their data — a frozen copy goes stale within hours and risks telling
  a family someone is safe/found/dead when they aren't.
- Each source is a pluggable, fail-soft adapter. One source failing must never
  fail the whole search.
- Records are deduped at QUERY TIME (entity resolution). A merged result keeps
  EVERY source attribution and surfaces a per-source verify/update link.
- Citizen-registry records are always tagged 'unverified'. Nothing here is
  presented as confirmed except ICRC's own confirmations.
"""
from .service import search, federated_search
from .models import PersonRecord, Query, MergedRecord

__all__ = ["search", "federated_search", "PersonRecord", "Query", "MergedRecord"]
