"""Claude pricing + cost math for the per-call cost meter.

Rates are USD per million tokens (MTok), input / output. Cached input is billed
at ~10% of the input rate (prompt caching). Update if Anthropic pricing changes.
"""
from __future__ import annotations

PRICING = {
    "claude-haiku-4-5":   {"in": 1.0,  "out": 5.0},
    "claude-sonnet-4-6":  {"in": 3.0,  "out": 15.0},
    "claude-opus-4-8":    {"in": 15.0, "out": 75.0},
}
_DEFAULT = {"in": 1.0, "out": 5.0}
_CACHE_DISCOUNT = 0.10  # cached input billed at ~10% of normal input rate


def cost_usd(model: str, in_tokens: int, out_tokens: int,
             cached_in_tokens: int = 0) -> float:
    p = PRICING.get(model, _DEFAULT)
    fresh_in = max(0, (in_tokens or 0) - (cached_in_tokens or 0))
    return (
        fresh_in / 1e6 * p["in"]
        + (cached_in_tokens or 0) / 1e6 * p["in"] * _CACHE_DISCOUNT
        + (out_tokens or 0) / 1e6 * p["out"]
    )
