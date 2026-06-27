"""Trust & safety screening for the hero network.

Two layers:
1. A deterministic, zero-cost regex screen that catches the high-precision abuse
   signals (advance-payment scams, payment rails, sexual/grooming content,
   off-platform luring).
2. An optional Claude (Haiku) screen for nuance the regex can't catch.

Plus minor detection: anything involving a child must never reach peer matching.

Design: fail toward safety. If the deterministic screen flags, we block without
calling the model. If the model is unavailable, we still honor the deterministic
result. Routing a borderline case to a vetted org is always safer than matching
a stranger.
"""
from __future__ import annotations

import re
import unicodedata

from . import config


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


# High-precision scam / payment-rail signals (advance-fee, money to strangers).
_MONEY = [
    r"\benvi[ae]s?\s+dinero", r"\bsend\s+money", r"\bpag[ao]\s+por\s+adelantado",
    r"\bpay\s+(first|up\s*front|in\s+advance)", r"\bdeposit[oa]\b", r"\bzelle\b",
    r"\bwestern\s*union\b", r"\bpaypal\b", r"\bcash\s*app\b", r"\bcashapp\b",
    r"\bgift\s*card", r"\btarjeta\s+de\s+regalo", r"\bbitcoin\b", r"\bcrypto\b",
    r"\busdt\b", r"\bcomisi[o]n\b", r"\bupfront\s+fee", r"\bpago\s+inicial",
]
# Sexual / grooming signals.
_SEXUAL = [
    r"\bnude", r"\bdesnud", r"\bfoto[s]?\s+(intim|sexual)", r"\bsexual\b",
    r"\bsexo\b", r"\bhot\s+pic", r"\bonlyfans\b",
]
# Off-platform luring / link-pushing.
_LURE = [
    r"\bagregam[e]?\s+a\b", r"\bescr[ií]beme\s+a\b", r"\btelegram\b",
    r"\bhaz\s+clic", r"\bclick\s+(here|este|el\s+enlace|the\s+link)",
    r"\bbit\.ly\b", r"\btinyurl\b", r"\bwa\.me/\d",
]
# Minor / child signals.
_MINOR_WORDS = [
    r"\bni[nñ][oa]s?\b", r"\bbeb[eé]s?\b", r"\bmenor(es)?\b", r"\binfante",
    r"\bhij[oa]s?\b", r"\bchild(ren)?\b", r"\bkid(s)?\b", r"\bbab(y|ies)\b",
    r"\bson\b", r"\bdaughter\b", r"\btoddler\b", r"\bnewborn\b",
]


def _any(patterns, text):
    return any(re.search(p, text) for p in patterns)


def detect_minor(text: str) -> bool:
    """True if the text plausibly involves someone under 18. Over-triggers on
    purpose — routing to a child-protection org is the safe direction."""
    t = _norm(text)
    if _any(_MINOR_WORDS, t):
        return True
    # explicit young age, e.g. "8 años" / "6 years"
    for m in re.finditer(r"\b(\d{1,2})\s*(anos|years?|yo|y/o)\b", t):
        if int(m.group(1)) < 18:
            return True
    return False


def screen_deterministic(text: str):
    """Return (ok, reason). reason in {money, sexual, lure} or None."""
    t = _norm(text)
    if _any(_MONEY, t):
        return False, "money"
    if _any(_SEXUAL, t):
        return False, "sexual"
    if _any(_LURE, t):
        return False, "lure"
    return True, None


_LLM_SYS = (
    "You screen short user posts for a humanitarian mutual-aid service. Reply with "
    "ONE word: 'ok' if safe, or one of 'money' (asks for payment/advance fee), "
    "'sexual' (sexual or grooming content), 'lure' (pushes off-platform or to a "
    "suspicious link), 'scam' (other clear scam). When unsure, reply 'ok'."
)
_LLM_REASONS = {"money", "sexual", "lure", "scam"}


def _screen_llm(text: str):
    """Best-effort model screen for nuance. Returns reason or None."""
    if not config.ANTHROPIC_API_KEY:
        return None
    try:
        from .llm import _client  # reuse the configured client
        from . import analytics
        resp = _client.messages.create(
            model=config.BOT_MODEL, max_tokens=5,
            system=[{"type": "text", "text": _LLM_SYS,
                     "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": text[:1000]}],
        )
        word = "".join(b.text for b in resp.content if b.type == "text").strip().lower()
        try:
            u = resp.usage
            analytics.record_llm_usage("safety", config.BOT_MODEL,
                                       getattr(u, "input_tokens", 0),
                                       getattr(u, "output_tokens", 0),
                                       getattr(u, "cache_read_input_tokens", 0) or 0)
        except Exception:
            pass
        return word if word in _LLM_REASONS else None
    except Exception:
        return None


def screen(text: str):
    """Full screen: deterministic first (free), then the model for nuance.
    Returns (ok: bool, reason: str|None)."""
    ok, reason = screen_deterministic(text)
    if not ok:
        return False, reason
    llm_reason = _screen_llm(text)
    if llm_reason:
        return False, llm_reason
    return True, None
