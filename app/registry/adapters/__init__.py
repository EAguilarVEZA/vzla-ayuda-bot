"""Source adapters. Register new sources by adding them to ALL_ADAPTERS."""
from .venezuela_te_busca import VenezuelaTeBuscaAdapter
from .desaparecidos import DesaparecidosAdapter
from .icrc import ICRCAdapter


def default_adapters():
    """The live source set, in the order results are preferred when tied."""
    return [
        ICRCAdapter(),               # authoritative, verified
        VenezuelaTeBuscaAdapter(),   # citizen registry, unverified
        DesaparecidosAdapter(),      # citizen registry, unverified (largest)
    ]


__all__ = [
    "VenezuelaTeBuscaAdapter", "DesaparecidosAdapter", "ICRCAdapter",
    "default_adapters",
]
