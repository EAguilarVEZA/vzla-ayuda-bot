"""Cost-optimization: keyword router (zero-token routing) + cost math."""
from app import costs


def test_keyword_router_avoids_llm_for_common_asks():
    from app.bot import keyword_intent
    assert keyword_intent("necesito un refugio en caracas") == "shelter"
    assert keyword_intent("busco a mi hermano") == "missing_persons"
    assert keyword_intent("quiero ser voluntario") == "hero_offer"
    assert keyword_intent("is this a scam?") == "scams"
    assert keyword_intent("how do i donate") == "how_to_help"
    # a sentence with no distinctive keyword falls through to the LLM
    assert keyword_intent("hello there, a quick question") is None


def test_haiku_is_the_default_model():
    from app import config
    assert config.BOT_MODEL == "claude-haiku-4-5"


def test_cost_math_and_cache_discount():
    # 1M input + 1M output on Haiku = $1 + $5
    assert round(costs.cost_usd("claude-haiku-4-5", 1_000_000, 1_000_000), 4) == 6.0
    # cached input is ~10% of input price: 1M cached in, 0 out = $0.10
    assert round(costs.cost_usd("claude-haiku-4-5", 1_000_000, 0,
                                cached_in_tokens=1_000_000), 4) == 0.10
    # unknown model falls back to a default rate (doesn't crash)
    assert costs.cost_usd("mystery", 1000, 1000) > 0
