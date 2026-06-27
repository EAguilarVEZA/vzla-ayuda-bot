"""SQLite store: users (language), the hero-network board (needs & offers,
stored bilingually), and per-user session state.

Cross-border by design: 'remote' help matches regardless of country;
'in person' help matches within the same region/location.
"""
import sqlite3
import time
from . import config

PEER_CATEGORIES = ["transporte", "insumos", "traduccion", "informacion", "busqueda"]
HIGH_RISK_CATEGORIES = ["alojamiento", "dinero", "menores"]

# Accept English synonyms -> canonical key
CATEGORY_ALIASES = {
    "transport": "transporte", "supplies": "insumos", "translation": "traduccion",
    "information": "informacion", "search": "busqueda", "housing": "alojamiento",
    "money": "dinero", "minors": "menores",
}


def canon_category(word: str):
    w = (word or "").strip().lower()
    w = CATEGORY_ALIASES.get(w, w)
    return w if w in (PEER_CATEGORIES + HIGH_RISK_CATEGORIES) else None


def _conn():
    c = sqlite3.connect(config.DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            user TEXT PRIMARY KEY, lang TEXT, created_at REAL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS posts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT NOT NULL,
            kind TEXT NOT NULL,            -- 'need' | 'offer'
            category TEXT NOT NULL,
            mode TEXT,                     -- 'remoto' | 'presencial'
            region TEXT,                   -- 'US' | 'VE' | 'other'
            location TEXT,
            desc_es TEXT, desc_en TEXT,
            contact TEXT, consent INTEGER DEFAULT 0,
            status TEXT DEFAULT 'open', created_at REAL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS sessions(
            user TEXT PRIMARY KEY, state TEXT, scratch TEXT, updated_at REAL)""")
        # Anonymized analytics. NO raw user, name, or free text is ever stored
        # here — only an intent, coarse location, language, and a per-DAY rotating
        # hash so we can count unique users per day without identifying anyone.
        c.execute("""CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL NOT NULL,
            day TEXT NOT NULL,             -- YYYY-MM-DD (UTC)
            intent TEXT,
            region TEXT,                   -- 'US' | 'VE' | 'other' | NULL
            location TEXT,                 -- coarse city/zone only (e.g. Caracas)
            lang TEXT,
            user_day_hash TEXT)""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_events_day ON events(day)")
        # Measured LLM usage + cost per call — feeds the dashboard cost panel.
        c.execute("""CREATE TABLE IF NOT EXISTS llm_usage(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL NOT NULL, day TEXT NOT NULL,
            kind TEXT,                     -- 'classify' | 'translate'
            model TEXT,
            in_tokens INTEGER, out_tokens INTEGER,
            cached_in_tokens INTEGER DEFAULT 0,
            cost_usd REAL)""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_usage_day ON llm_usage(day)")
        # --- Trust & safety ---
        c.execute("""CREATE TABLE IF NOT EXISTS reports(
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL,
            reporter TEXT, target_contact TEXT, reason TEXT, text TEXT,
            status TEXT DEFAULT 'open')""")   # status: open | reviewed
        c.execute("""CREATE TABLE IF NOT EXISTS blocks(
            blocker TEXT, blocked_contact TEXT, ts REAL,
            PRIMARY KEY(blocker, blocked_contact))""")
        c.execute("""CREATE TABLE IF NOT EXISTS bans(
            user TEXT PRIMARY KEY, ts REAL, reason TEXT)""")
        # Close-the-loop: a queue of pending notifications (e.g. new matches),
        # delivered the next time the user messages.
        c.execute("""CREATE TABLE IF NOT EXISTS notifications(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT, text TEXT, created_at REAL, delivered INTEGER DEFAULT 0)""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user,delivered)")
        # Org-facing portal: partner orgs (API keys), the live capacity they push
        # back (shelters/food/clinics), and the needs they claim to cover.
        c.execute("""CREATE TABLE IF NOT EXISTS partners(
            api_key TEXT PRIMARY KEY, name TEXT, verified INTEGER DEFAULT 1,
            created_at REAL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS capacity(
            id INTEGER PRIMARY KEY AUTOINCREMENT, partner TEXT,
            type TEXT, location TEXT, name TEXT, detail TEXT,
            status TEXT DEFAULT 'open', updated_at REAL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS claims(
            id INTEGER PRIMARY KEY AUTOINCREMENT, partner TEXT,
            category TEXT, location TEXT, note TEXT, created_at REAL)""")
        # Migrations for columns added after first release (ignore if present).
        for stmt in (
            "ALTER TABLE users ADD COLUMN verified INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN alerts INTEGER DEFAULT 0",
            "ALTER TABLE posts ADD COLUMN safety TEXT DEFAULT 'ok'",
        ):
            try:
                c.execute(stmt)
            except Exception:
                pass


# ---- users / language ----
def user_exists(user):
    with _conn() as c:
        return c.execute("SELECT 1 FROM users WHERE user=?", (user,)).fetchone() is not None


def get_lang(user, default="es"):
    with _conn() as c:
        row = c.execute("SELECT lang FROM users WHERE user=?", (user,)).fetchone()
        return row["lang"] if row and row["lang"] else default


def set_lang(user, lang):
    with _conn() as c:
        c.execute("""INSERT INTO users(user,lang,created_at) VALUES(?,?,?)
                     ON CONFLICT(user) DO UPDATE SET lang=?""",
                  (user, lang, time.time(), lang))


# ---- sessions ----
def get_session(user):
    with _conn() as c:
        row = c.execute("SELECT state,scratch FROM sessions WHERE user=?", (user,)).fetchone()
        return (row["state"], row["scratch"]) if row else (None, None)


def set_session(user, state, scratch):
    with _conn() as c:
        c.execute("""INSERT INTO sessions(user,state,scratch,updated_at) VALUES(?,?,?,?)
                     ON CONFLICT(user) DO UPDATE SET state=?,scratch=?,updated_at=?""",
                  (user, state, scratch, time.time(), state, scratch, time.time()))


def clear_session(user):
    with _conn() as c:
        c.execute("DELETE FROM sessions WHERE user=?", (user,))


# ---- hero-network posts ----
def add_post(user, kind, category, mode, region, location, desc_es, desc_en, contact, consent):
    with _conn() as c:
        cur = c.execute("""INSERT INTO posts
            (user,kind,category,mode,region,location,desc_es,desc_en,contact,consent,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (user, kind, category, mode, region, location, desc_es, desc_en,
             contact, int(consent), time.time()))
        return cur.lastrowid


def find_matches(kind, category, mode, region, location, limit=3, viewer=None):
    """A need looks for offers (and vice-versa). Remote = cross-border OK;
    in person = same region (and location if both given).

    Trust & safety: only 'open' + safety='ok' posts from non-banned authors are
    eligible; anything the viewer has blocked is excluded; verified helpers and
    cross-border matches are surfaced first."""
    want = "offer" if kind == "need" else "need"
    banned = _banned_set()
    blocked = _blocked_contacts(viewer) if viewer else set()
    with _conn() as c:
        rows = c.execute(
            """SELECT p.*, COALESCE(u.verified,0) AS verified FROM posts p
               LEFT JOIN users u ON u.user = p.user
               WHERE p.kind=? AND p.category=? AND p.status='open'
                 AND p.consent=1 AND COALESCE(p.safety,'ok')='ok'
               ORDER BY p.created_at DESC""",
            (want, category)).fetchall()
    candidates = []
    for r in rows:
        r = dict(r)
        if r["user"] in banned or (r.get("contact") in blocked):
            continue
        remote = (mode == "remoto") or (r.get("mode") == "remoto")
        if remote:
            qualifies = True
        elif region and r.get("region") and region == r["region"]:
            qualifies = (not location or not r.get("location")
                         or location.lower() == r["location"].lower())
        else:
            qualifies = False
        if not qualifies:
            continue
        r["_cross_border"] = bool(remote and region and r.get("region")
                                  and region != r["region"])
        r["_verified"] = bool(r.get("verified"))
        candidates.append(r)
    # Verified first, then cross-border, then recency (stable sort).
    candidates.sort(key=lambda r: (0 if r["_verified"] else 1,
                                   0 if r["_cross_border"] else 1))
    return candidates[:limit]


def list_open(kind, limit=5, viewer=None):
    banned = _banned_set()
    blocked = _blocked_contacts(viewer) if viewer else set()
    with _conn() as c:
        rows = c.execute(
            """SELECT p.*, COALESCE(u.verified,0) AS verified FROM posts p
               LEFT JOIN users u ON u.user = p.user
               WHERE p.kind=? AND p.status='open' AND p.consent=1
                 AND COALESCE(p.safety,'ok')='ok'
               ORDER BY p.created_at DESC""", (kind,)).fetchall()
    out = []
    for r in rows:
        r = dict(r)
        if r["user"] in banned or (r.get("contact") in blocked):
            continue
        r["_verified"] = bool(r.get("verified"))
        out.append(r)
        if len(out) >= limit:
            break
    return out


def count_posts_today(user):
    cutoff = time.time() - 86400
    with _conn() as c:
        return c.execute("SELECT COUNT(*) n FROM posts WHERE user=? AND created_at>=?",
                         (user, cutoff)).fetchone()["n"]


def suspend_posts_by_contact(contact):
    """Auto-suspend on report: hide a contact's posts pending human review."""
    if not contact:
        return 0
    with _conn() as c:
        cur = c.execute("UPDATE posts SET status='suspended' WHERE contact=?", (contact,))
        return cur.rowcount


# ---- trust & safety: reports / blocks / bans / verification ----
def add_report(reporter, target_contact, reason, text):
    with _conn() as c:
        c.execute("""INSERT INTO reports(ts,reporter,target_contact,reason,text)
                     VALUES(?,?,?,?,?)""",
                  (time.time(), reporter, target_contact, reason, text))


def add_block(blocker, blocked_contact):
    with _conn() as c:
        c.execute("""INSERT OR IGNORE INTO blocks(blocker,blocked_contact,ts)
                     VALUES(?,?,?)""", (blocker, blocked_contact, time.time()))


def _blocked_contacts(user):
    with _conn() as c:
        return {r["blocked_contact"] for r in
                c.execute("SELECT blocked_contact FROM blocks WHERE blocker=?", (user,)).fetchall()}


def ban_user(user, reason="abuse"):
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO bans(user,ts,reason) VALUES(?,?,?)",
                  (user, time.time(), reason))
        c.execute("UPDATE posts SET status='suspended' WHERE user=?", (user,))


def is_banned(user):
    with _conn() as c:
        return c.execute("SELECT 1 FROM bans WHERE user=?", (user,)).fetchone() is not None


def _banned_set():
    with _conn() as c:
        return {r["user"] for r in c.execute("SELECT user FROM bans").fetchall()}


def set_verified(user, verified=True):
    with _conn() as c:
        c.execute("""INSERT INTO users(user,lang,created_at,verified) VALUES(?,?,?,?)
                     ON CONFLICT(user) DO UPDATE SET verified=?""",
                  (user, "es", time.time(), int(verified), int(verified)))


def is_verified(user):
    with _conn() as c:
        row = c.execute("SELECT verified FROM users WHERE user=?", (user,)).fetchone()
        return bool(row and row["verified"])


# ---- close-the-loop: resolve / notify / alerts ----
def resolve_user_posts(user):
    """Mark a user's open posts as resolved (they got/ gave the help)."""
    with _conn() as c:
        cur = c.execute("UPDATE posts SET status='resolved' WHERE user=? AND status='open'",
                        (user,))
        return cur.rowcount


def add_notification(user, text):
    with _conn() as c:
        c.execute("INSERT INTO notifications(user,text,created_at,delivered) VALUES(?,?,?,0)",
                  (user, text, time.time()))


def has_pending(user):
    with _conn() as c:
        return c.execute("SELECT 1 FROM notifications WHERE user=? AND delivered=0 LIMIT 1",
                         (user,)).fetchone() is not None


def pop_notifications(user, limit=5):
    """Return undelivered notifications and mark them delivered."""
    with _conn() as c:
        rows = c.execute("""SELECT id,text FROM notifications
                            WHERE user=? AND delivered=0 ORDER BY created_at LIMIT ?""",
                         (user, limit)).fetchall()
        ids = [r["id"] for r in rows]
        if ids:
            c.execute(f"UPDATE notifications SET delivered=1 WHERE id IN "
                      f"({','.join('?' * len(ids))})", ids)
        return [r["text"] for r in rows]


def set_alerts(user, on=True):
    with _conn() as c:
        c.execute("""INSERT INTO users(user,lang,created_at,alerts) VALUES(?,?,?,?)
                     ON CONFLICT(user) DO UPDATE SET alerts=?""",
                  (user, "es", time.time(), int(on), int(on)))


def get_alerts(user):
    with _conn() as c:
        row = c.execute("SELECT alerts FROM users WHERE user=?", (user,)).fetchone()
        return bool(row and row["alerts"])


def alert_subscribers():
    with _conn() as c:
        return [r["user"] for r in
                c.execute("SELECT user FROM users WHERE alerts=1").fetchall()]


def moderation_summary():
    with _conn() as c:
        open_reports = c.execute("SELECT COUNT(*) n FROM reports WHERE status='open'").fetchone()["n"]
        suspended = c.execute("SELECT COUNT(*) n FROM posts WHERE status='suspended'").fetchone()["n"]
        flagged = c.execute("SELECT COUNT(*) n FROM posts WHERE COALESCE(safety,'ok')!='ok'").fetchone()["n"]
        banned = c.execute("SELECT COUNT(*) n FROM bans").fetchone()["n"]
    return {"open_reports": open_reports, "suspended_posts": suspended,
            "flagged_posts": flagged, "banned_users": banned}


def wipe_user(user):
    with _conn() as c:
        c.execute("DELETE FROM posts WHERE user=?", (user,))
        c.execute("DELETE FROM sessions WHERE user=?", (user,))
        c.execute("DELETE FROM users WHERE user=?", (user,))
        c.execute("DELETE FROM blocks WHERE blocker=?", (user,))
        c.execute("DELETE FROM notifications WHERE user=?", (user,))
