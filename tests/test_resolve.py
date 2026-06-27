"""Unit tests for query-time entity resolution (the dedupe core)."""
from app.registry.models import (
    PersonRecord, STATUS_MISSING, STATUS_SAFE, STATUS_UNKNOWN,
)
from app.registry import resolve as R


def rec(name, source="S", **kw):
    return PersonRecord(full_name=name, source=source,
                        source_url=f"http://{source}", **kw)


# --- name normalization -----------------------------------------------------
def test_strip_accents_and_nicknames():
    assert R.normalize_name("José Pérez") == "jose perez"
    assert R.normalize_name("Pepe Pérez") == "jose perez"   # nickname canonical
    assert R.normalize_name("María de los Ángeles") == "maria angeles"  # stopwords


def test_similarity_reordered_names_high():
    assert R.name_similarity("Maria Jose Perez", "Perez Maria Jose") >= 0.82


def test_similarity_dropped_surname():
    # one-surname vs two-surname should still be considered the same person
    assert R.name_similarity("Jose Perez", "Jose Perez Gomez") >= 0.82


def test_similarity_different_people_low():
    assert R.name_similarity("Jose Perez", "Carlos Rodriguez") < 0.82


# --- merge decisions --------------------------------------------------------
def test_same_person_merges_across_sources():
    a = rec("José Pérez", source="A", age=34, location="La Guaira",
            status=STATUS_MISSING)
    b = rec("Jose Perez Gomez", source="B", age=34, location="La Guaira",
            status=STATUS_SAFE)
    merged = R.resolve([a, b])
    assert len(merged) == 1
    assert len(merged[0].sources) == 2
    # strongest signal (safe) surfaces, both sources preserved
    assert merged[0].status == STATUS_SAFE


def test_age_mismatch_blocks_merge():
    a = rec("Jose Perez", age=30)
    b = rec("Jose Perez", age=70)
    assert len(R.resolve([a, b])) == 2


def test_different_people_not_merged():
    a = rec("Jose Perez", age=34)
    b = rec("Carlos Rodriguez", age=34)
    assert len(R.resolve([a, b])) == 2


def test_verified_sorts_first():
    a = rec("Ana Diaz", source="citizen", verified=False, status=STATUS_MISSING)
    b = rec("Beatriz Ruiz", source="ICRC", verified=True, status=STATUS_SAFE)
    merged = R.resolve([a, b])
    assert merged[0].any_verified is True


def test_link_only_not_merged_into_people():
    link = PersonRecord(full_name="Jose Perez", source="Reg",
                        source_url="http://reg", status=STATUS_UNKNOWN,
                        note="search here")
    person = rec("Jose Perez", age=34, status=STATUS_MISSING)
    merged = R.resolve([link, person])
    # the link-only fallback stays separate from the real person record
    assert len(merged) == 2
    assert any(m.sources[0].is_link_only for m in merged)
