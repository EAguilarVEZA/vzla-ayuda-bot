"""Tests for the federated service: fan-out, fail-soft isolation, parsing,
and safety-first rendering."""
from app.registry.base import SourceAdapter
from app.registry.models import Query, PersonRecord, STATUS_MISSING, STATUS_SAFE
from app.registry.service import federated_search
from app.registry.render import render_results_es
from app.registry._parse import parse_generic_hits


class FakeAdapter(SourceAdapter):
    def __init__(self, name, hits, verified=False):
        self.name = name
        self.verified = verified
        self._hits = hits
        self.search_page = f"http://{name}/?q={{q}}"

    def search(self, query):
        return parse_generic_hits(self._hits, source=self.name,
                                  verified=self.verified,
                                  fallback_url=self.deep_link(query))


class BoomAdapter(SourceAdapter):
    name = "Boom"
    search_page = "http://boom"

    def search(self, query):
        raise RuntimeError("source down")


def test_failing_adapter_is_isolated():
    good = FakeAdapter("Good", [{"name": "Jose Perez", "edad": 40,
                                  "estado": "desaparecido"}])
    results = federated_search(Query("Jose Perez"),
                               adapters=[BoomAdapter(), good])
    # the healthy source still returns despite the other throwing
    assert len(results) == 1
    assert results[0].full_name == "Jose Perez"


def test_cross_source_dedupe_and_status():
    a = FakeAdapter("Reg A", [{"nombre": "Jose Perez", "edad": 34,
                               "ubicacion": "Caracas", "estado": "desaparecido"}])
    b = FakeAdapter("ICRC", [{"name": "Jose Perez Gomez", "age": 34,
                              "location": "Caracas", "status": "found"}],
                    verified=True)
    results = federated_search(Query("Jose Perez"), adapters=[a, b])
    assert len(results) == 1
    m = results[0]
    assert len(m.sources) == 2          # both kept
    assert m.status == STATUS_SAFE       # 'found' wins over 'missing'
    assert m.any_verified is True


def test_empty_name_returns_nothing():
    from app.registry.service import search
    assert search("") == []


def test_render_includes_safety_labels():
    a = FakeAdapter("Venezuela Te Busca",
                    [{"nombre": "Ana Diaz", "edad": 22, "estado": "desaparecida"}])
    results = federated_search(Query("Ana Diaz"), adapters=[a])
    out = render_results_es("Ana Diaz", results)
    assert "Ana Diaz" in out
    assert "sin verificar" in out                 # unverified tag present
    assert "familylinks.icrc.org" in out          # ICRC handoff present
    assert "dinero" in out.lower()                # money-scam warning present
    assert "Verificar/actualizar" in out          # per-source verify link


def test_render_no_results():
    out = render_results_es("Nadie", [])
    assert "No encontramos" in out
    assert "familylinks.icrc.org" in out
