"""Privacy-preserving analytics: what's happening, where, and what's unmet.

This is the data layer behind the management dashboard and the needs heatmap.

Privacy by design (honors the project guardrails):
- We never log a phone number, a name, or any free text the user typed.
- We log only: intent, coarse location (city/zone), region, language, timestamp.
- To count UNIQUE users per day without identifying them, we store a per-day
  rotating hash = sha256(user + day + salt). It can't be linked across days and
  can't be reversed to a phone number.
- 'DELETE' / 'BORRAR' wipes a user's posts/sessions; events hold no identifier,
  so there is nothing personal left to erase.
"""
from __future__ import annotations

import hashlib
import os
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta

from . import matching as M
from . import costs

# Rotating salt so per-day hashes can't be precomputed against a phone book.
_SALT = os.getenv("ANALYTICS_SALT", "con-venezuela")

# Intents that represent a real NEED (vs navigation/menu/etc.) — used to compute
# "what's needed where" and unmet-need gaps.
NEED_INTENTS = {"shelter", "food", "medical", "supplies", "mental_health",
                "missing_persons", "hero_need"}


def _today_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _user_day_hash(user: str, day: str) -> str:
    return hashlib.sha256(f"{user}|{day}|{_SALT}".encode()).hexdigest()[:16]


def log_event(user, intent, region=None, location=None, lang=None):
    """Record one anonymized interaction. Best-effort: never breaks the bot."""
    try:
        day = _today_utc()
        with M._conn() as c:
            c.execute(
                """INSERT INTO events(ts,day,intent,region,location,lang,user_day_hash)
                   VALUES(?,?,?,?,?,?,?)""",
                (time.time(), day, intent, region,
                 (location or None), lang, _user_day_hash(user, day)),
            )
    except Exception:
        pass


def record_llm_usage(kind, model, in_tokens, out_tokens, cached_in_tokens=0):
    """Log one Claude call's measured token usage + cost. Best-effort."""
    try:
        c_usd = costs.cost_usd(model, in_tokens, out_tokens, cached_in_tokens)
        day = _today_utc()
        with M._conn() as c:
            c.execute(
                """INSERT INTO llm_usage(ts,day,kind,model,in_tokens,out_tokens,
                                         cached_in_tokens,cost_usd)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (time.time(), day, kind, model, in_tokens or 0, out_tokens or 0,
                 cached_in_tokens or 0, c_usd))
    except Exception:
        pass


def llm_cost_summary(days: int = 14) -> dict:
    """Measured AI cost (from real token usage), for the dashboard cost panel."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    by_kind = defaultdict(lambda: {"calls": 0, "cost_usd": 0.0,
                                   "in_tokens": 0, "out_tokens": 0, "cached_in_tokens": 0})
    total = 0.0
    with M._conn() as c:
        rows = c.execute("SELECT * FROM llm_usage WHERE day >= ?", (cutoff,)).fetchall()
    for r in rows:
        k = by_kind[r["kind"] or "other"]
        k["calls"] += 1
        k["cost_usd"] += r["cost_usd"] or 0
        k["in_tokens"] += r["in_tokens"] or 0
        k["out_tokens"] += r["out_tokens"] or 0
        k["cached_in_tokens"] += r["cached_in_tokens"] or 0
        total += r["cost_usd"] or 0
    return {"total_usd": round(total, 4),
            "by_kind": {k: {**v, "cost_usd": round(v["cost_usd"], 4)}
                        for k, v in by_kind.items()}}


# ---------------------------------------------------------------- aggregation
def _rows_since(days: int):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    with M._conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM events WHERE day >= ? ORDER BY ts", (cutoff,)).fetchall()]


def daily_summary(days: int = 14) -> dict:
    """Everything the dashboard needs, aggregated and PII-free."""
    rows = _rows_since(days)

    by_day = defaultdict(lambda: {"events": 0, "users": set()})
    by_intent = Counter()
    by_lang = Counter()
    needs_by_loc = defaultdict(Counter)   # location -> Counter(intent)
    by_region = Counter()

    for r in rows:
        d = by_day[r["day"]]
        d["events"] += 1
        if r["user_day_hash"]:
            d["users"].add(r["user_day_hash"])
        if r["intent"]:
            by_intent[r["intent"]] += 1
        if r["lang"]:
            by_lang[r["lang"]] += 1
        if r["region"]:
            by_region[r["region"]] += 1
        if r["intent"] in NEED_INTENTS and r["location"]:
            needs_by_loc[r["location"]][r["intent"]] += 1

    trend = [{"day": day, "events": v["events"], "users": len(v["users"])}
             for day, v in sorted(by_day.items())]

    heatmap = []
    for loc, counter in needs_by_loc.items():
        heatmap.append({"location": loc, "total": sum(counter.values()),
                        "by_intent": dict(counter)})
    heatmap.sort(key=lambda x: x["total"], reverse=True)

    return {
        "window_days": days,
        "totals": {
            "events": len(rows),
            "unique_users": len({r["user_day_hash"] for r in rows if r["user_day_hash"]}),
            "needs": sum(1 for r in rows if r["intent"] in NEED_INTENTS),
        },
        "trend": trend,
        "by_intent": by_intent.most_common(),
        "by_language": by_lang.most_common(),
        "by_region": by_region.most_common(),
        "needs_heatmap": heatmap,
        "hero_network": hero_supply_demand(),
        "ai_cost": llm_cost_summary(days),
        "moderation": M.moderation_summary(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def hero_supply_demand() -> list:
    """For each hero-network category: how many need help vs how many offer it.
    A 'gap' (needs > offers) is where to route volunteers/resources next.
    Reads the posts board (already consented + anonymized at the contact level)."""
    with M._conn() as c:
        rows = c.execute(
            """SELECT category, kind, COUNT(*) n FROM posts
               WHERE status='open' GROUP BY category, kind""").fetchall()
    agg = defaultdict(lambda: {"need": 0, "offer": 0})
    for r in rows:
        agg[r["category"]][r["kind"]] += r["n"]
    out = [{"category": cat, "need": v["need"], "offer": v["offer"],
            "gap": v["need"] - v["offer"]} for cat, v in agg.items()]
    out.sort(key=lambda x: x["gap"], reverse=True)
    return out
