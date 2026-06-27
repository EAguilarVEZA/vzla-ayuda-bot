"""Query-time entity resolution for missing-persons records.

Deduplicate records that refer to the same person across registries, WITHOUT an
LLM on the hot path — deterministic, fast, and unit-testable. Spanish-aware:
strips accents, normalizes nicknames, and tolerates the one-surname vs
two-surname mismatch common in Venezuelan names.

This is intentionally conservative: when in doubt we DO NOT merge, because
wrongly merging two different people is worse than showing a family two entries.
"""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import List

from .models import PersonRecord, MergedRecord

# Spanish nickname -> canonical given name (extend as needed).
_NICKNAMES = {
    "pepe": "jose", "pepito": "jose", "chepe": "jose",
    "paco": "francisco", "pancho": "francisco", "kiko": "francisco",
    "lalo": "eduardo", "guayo": "eduardo",
    "nacho": "ignacio",
    "chuy": "jesus", "chucho": "jesus",
    "memo": "guillermo",
    "toño": "antonio", "tono": "antonio",
    "beto": "alberto", "tito": "alberto",
    "lupe": "guadalupe", "lupita": "guadalupe",
    "mari": "maria", "maria": "maria", "mary": "maria", "mari": "maria",
    "cris": "cristina", "tina": "cristina",
    "isa": "isabel", "chabela": "isabel",
}

# Tokens that carry no identifying signal.
_STOPWORDS = {"de", "del", "la", "las", "los", "y", "san", "santa"}

_AGE_TOLERANCE = 1            # years
_NAME_THRESHOLD = 0.82       # token-set similarity needed to merge
_STRONG_TOKEN_OVERLAP = 0.60  # min Jaccard of significant tokens


def strip_accents(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_name(name: str) -> str:
    """Lowercase, de-accent, strip punctuation, drop honorifics/stopwords,
    and canonicalize known nicknames. Returns a normalized whitespace string."""
    s = strip_accents((name or "").lower())
    s = re.sub(r"[^a-z\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    tokens = []
    for tok in s.split():
        if tok in _STOPWORDS:
            continue
        tokens.append(_NICKNAMES.get(tok, tok))
    return " ".join(tokens)


def name_tokens(name: str) -> set:
    return set(normalize_name(name).split())


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def name_similarity(a: str, b: str) -> float:
    """Blend token-set Jaccard with character-level ratio of the sorted tokens.

    Handles two common cases:
    - reordered / partial names ("Maria Jose Perez" vs "Perez Maria")
    - one-surname vs two-surname ("Jose Perez" vs "Jose Perez Gomez")
    """
    ta, tb = name_tokens(a), name_tokens(b)
    if not ta or not tb:
        return 0.0

    jac = _jaccard(ta, tb)

    # Subset bonus: if the smaller name's tokens are fully contained in the
    # larger (the dropped-second-surname case), treat as a strong match.
    smaller, larger = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    containment = len(smaller & larger) / len(smaller)

    sa = " ".join(sorted(ta))
    sb = " ".join(sorted(tb))
    seq = SequenceMatcher(None, sa, sb).ratio()

    # Weighted blend; containment rewards the surname-dropping case.
    return max(jac, 0.5 * containment + 0.5 * seq, 0.6 * containment + 0.4 * jac)


def _age_compatible(a, b) -> bool:
    if a is None or b is None:
        return True
    return abs(a - b) <= _AGE_TOLERANCE


def _location_compatible(a: str, b: str) -> bool:
    if not a or not b:
        return True
    na, nb = strip_accents(a.lower()), strip_accents(b.lower())
    return na in nb or nb in na or _jaccard(set(na.split()), set(nb.split())) > 0


def same_person(r1: PersonRecord, r2: PersonRecord) -> bool:
    """Conservative match decision used by the clustering pass."""
    if not _age_compatible(r1.age, r2.age):
        return False
    if not _location_compatible(r1.location or "", r2.location or ""):
        return False
    sim = name_similarity(r1.full_name, r2.full_name)
    if sim >= _NAME_THRESHOLD:
        return True
    # A slightly lower name score still merges if age+location both corroborate.
    if (sim >= 0.74
            and r1.age is not None and r2.age is not None
            and _jaccard(name_tokens(r1.full_name), name_tokens(r2.full_name)) >= _STRONG_TOKEN_OVERLAP):
        return True
    return False


def resolve(records: List[PersonRecord]) -> List[MergedRecord]:
    """Cluster records into people (single-link agglomeration) and merge each
    cluster into one MergedRecord. Order-independent and deterministic.

    Link-only fallback records (a registry's "search here" page) are never
    merged into a person cluster — they are appended as their own entries so the
    family always sees where else to look."""
    people: List[PersonRecord] = [r for r in records if not r.is_link_only]
    links: List[PersonRecord] = [r for r in records if r.is_link_only]

    clusters: List[List[PersonRecord]] = []
    for rec in people:
        placed = False
        for cluster in clusters:
            if any(same_person(rec, other) for other in cluster):
                cluster.append(rec)
                placed = True
                break
        if not placed:
            clusters.append([rec])

    merged = [MergedRecord.from_records(c) for c in clusters]

    # Sort: verified first, then richer (more sources), then most recent.
    merged.sort(key=lambda m: (m.any_verified, len(m.sources),
                               m.best_reported_at or ""), reverse=True)

    # Append link-only fallbacks as their own single-source merged entries.
    for link in links:
        merged.append(MergedRecord.from_records([link]))
    return merged
