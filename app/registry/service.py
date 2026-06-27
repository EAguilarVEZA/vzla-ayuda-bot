"""Federated search service: fan out to every adapter in parallel, isolate
failures, then dedupe the combined results at query time.

Stateless by design: nothing here is written to a database. Missing-persons PII
is queried live and discarded after the reply is rendered.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

from .models import Query, PersonRecord, MergedRecord
from .resolve import resolve
from .adapters import default_adapters

log = logging.getLogger("registry")


def _safe_search(adapter, query: Query) -> List[PersonRecord]:
    """Run one adapter with a hard timeout; never let it crash the search."""
    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(adapter.search, query)
            return fut.result(timeout=getattr(adapter, "timeout_s", 4.0)) or []
    except Exception as e:  # timeout, parse error, network — all isolated
        log.warning("adapter %s failed: %s", getattr(adapter, "name", "?"), e)
        return []


def federated_search(query: Query, adapters=None) -> List[MergedRecord]:
    """Query all sources concurrently and return deduped, ranked people."""
    adapters = adapters if adapters is not None else default_adapters()
    all_records: List[PersonRecord] = []

    with ThreadPoolExecutor(max_workers=max(1, len(adapters))) as ex:
        futures = {ex.submit(_safe_search, a, query): a for a in adapters}
        for fut in as_completed(futures):
            all_records.extend(fut.result())

    return resolve(all_records)


def search(name: str, age: Optional[int] = None,
           location: Optional[str] = None, adapters=None) -> List[MergedRecord]:
    """Convenience entry point used by the bot."""
    name = (name or "").strip()
    if not name:
        return []
    return federated_search(Query(name=name, age=age, location=location), adapters)
