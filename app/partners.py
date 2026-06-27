"""Org-facing portal data layer: partner orgs, their live capacity, and claims.

Relief orgs authenticate with an API key. They can:
- read the (anonymized, aggregated) needs picture,
- push live capacity (shelters/food points/clinics) that the BOT then surfaces
  to people — closing the loop between what's needed and what's available,
- claim a need category+location so coordinators can see who's covering what.

No citizen PII is exposed through this layer — orgs act on aggregate needs, not
individuals.
"""
from __future__ import annotations

import secrets
import time

from . import matching as M

CAPACITY_TYPES = ("shelter", "food", "water", "medical")
STATUSES = ("open", "limited", "full")


# ---- partners / auth ----
def create_partner(name, verified=True):
    key = "vzla_" + secrets.token_urlsafe(24)
    with M._conn() as c:
        c.execute("INSERT INTO partners(api_key,name,verified,created_at) VALUES(?,?,?,?)",
                  (key, name, int(verified), time.time()))
    return key


def get_partner(api_key):
    if not api_key:
        return None
    with M._conn() as c:
        row = c.execute("SELECT * FROM partners WHERE api_key=?", (api_key,)).fetchone()
        return dict(row) if row else None


# ---- capacity (pushed by orgs, surfaced by the bot) ----
def add_capacity(partner, type_, location, name, detail="", status="open"):
    type_ = (type_ or "").lower()
    status = status if status in STATUSES else "open"
    with M._conn() as c:
        cur = c.execute(
            """INSERT INTO capacity(partner,type,location,name,detail,status,updated_at)
               VALUES(?,?,?,?,?,?,?)""",
            (partner, type_, location, name, detail, status, time.time()))
        return cur.lastrowid


def list_capacity(type_=None, location=None, status=None, limit=50):
    q = "SELECT * FROM capacity WHERE 1=1"
    args = []
    if type_:
        q += " AND type=?"; args.append(type_.lower())
    if location:
        q += " AND lower(location)=?"; args.append(location.lower())
    if status:
        q += " AND status=?"; args.append(status)
    q += " ORDER BY updated_at DESC LIMIT ?"; args.append(limit)
    with M._conn() as c:
        return [dict(r) for r in c.execute(q, args).fetchall()]


def set_capacity_status(cap_id, status):
    with M._conn() as c:
        c.execute("UPDATE capacity SET status=?, updated_at=? WHERE id=?",
                  (status, time.time(), cap_id))


# ---- claims (who is covering what) ----
def add_claim(partner, category, location, note=""):
    with M._conn() as c:
        cur = c.execute(
            "INSERT INTO claims(partner,category,location,note,created_at) VALUES(?,?,?,?,?)",
            (partner, category, location, note, time.time()))
        return cur.lastrowid


def list_claims(category=None, location=None, limit=100):
    q = "SELECT * FROM claims WHERE 1=1"
    args = []
    if category:
        q += " AND category=?"; args.append(category)
    if location:
        q += " AND lower(location)=?"; args.append(location.lower())
    q += " ORDER BY created_at DESC LIMIT ?"; args.append(limit)
    with M._conn() as c:
        return [dict(r) for r in c.execute(q, args).fetchall()]
