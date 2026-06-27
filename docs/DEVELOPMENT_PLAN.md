# Ayuda Venezuela Bot — Development Plan

_Con Venezuela earthquake-relief initiative · companion to `HANDOFF.md`_
_Architecture diagram: `docs/architecture.svg`_

This plan turns the backlog in `HANDOFF.md §5` into an ordered, buildable sequence.
Each phase lists **what**, **why it's in this order**, **done-when** acceptance
criteria, and the **guardrails** (`HANDOFF.md §3`) that constrain it. We build the
**federated registry-search module first** (Phase 1), per decision.

---

## Guardrails that bind every phase (non-negotiable)

These are not features; they are constraints checked at every step.

- **Missing-persons data = federated live search, never bulk scrape/rehost.** Query
  public registries + ICRC at request time; dedupe at query time; return results with
  **source + "unverified" + a verify/update link**. A frozen copy goes stale within
  hours and can tell a family someone is safe/found/dead when they aren't.
- **Consent before sharing any contact.** Contacts surface only after explicit yes.
- **High-risk → vetted orgs, not strangers.** Housing, money, and minors auto-redirect
  to Caritas / Red Cross / churches instead of peer matching.
- **Never money to strangers.** Money-scam warning on every match and browse result.
- **Minimal data + wipe.** Store the minimum; `DELETE`/`BORRAR` wipes a user completely.
- **Grounded answers only.** The bot speaks from `resources.yaml`; it never invents
  shelters, numbers, or organizations.
- **Sanctions/OFAC.** Give through established orgs; never wire to individuals.

---

## Phase 0 — Repository hygiene & local run (0.5 day)

**What.** Pin the environment, get the existing bot running locally, lock in tests.

- Create/confirm `.venv`, `pip install -r requirements.txt`.
- `cp .env.example .env`; add `ANTHROPIC_API_KEY` (Twilio creds optional for offline work).
- Add a `tests/` folder and a `pytest` dev dependency; port the existing offline smoke
  test into a runnable `test_smoke.py`.
- Add `BOT_MODEL=claude-haiku-4-5` to `.env` (config currently defaults to sonnet).

**Done when.** `uvicorn app.main:app --reload` boots; `GET /` returns ok; `pytest` green.

---

## Phase 1 — Federated registry-search module (FIRST FEATURE BUILD, 2–3 days)

The highest-value new capability and the one with the sharpest safety edge.

### 1a. Adapter contract & data model
- New package `app/registry/`.
- `base.py` defines a `SourceAdapter` protocol: `search(query) -> list[PersonRecord]`,
  plus `name`, `verify_url(record)`, and a `verified: bool` flag (always `False` for
  citizen registries, `True` only for ICRC's own confirmations).
- `models.py` defines `PersonRecord` (normalized): `full_name`, `given`, `family`,
  `age`, `location`, `status` (`reported_missing` / `marked_safe` / `unknown`),
  `source`, `source_url`, `reported_at`, `raw`.
- `Query` dataclass: `name`, optional `age`, optional `location`.

### 1b. Source adapters (pluggable, isolated, fail-soft)
- `venezuela_te_busca.py`, `desaparecidos.py`, `icrc.py`.
- Each is a thin, **read-only, live** client. **No bulk download, no local copy.**
  One adapter failing must never fail the whole search (catch + log, return `[]`).
- Per-source timeout (e.g. 4s) so a slow registry can't hang a WhatsApp reply.
- **First task inside this phase: confirm each source's real public query surface**
  (search endpoint / params / response shape) before coding the parser — build parsers
  around observed responses, not assumptions. If a source has no machine-readable
  query surface, the adapter degrades to returning the registry's deep-link search URL
  as a single "search here" result rather than fabricating records.

### 1c. Query-time dedupe / entity resolution (Edgar's wheelhouse)
- `resolve.py` merges records that refer to the same person across sources.
- Blocking key + similarity: normalized name (unidecode, lowercase, strip honorifics),
  optional age tolerance (±1), optional location match.
- Name similarity via token-set ratio + a Spanish-aware nickname/compound-surname map
  (e.g. "José"≈"Jose", two-surname vs one-surname). Deterministic, testable, no LLM
  on the hot path.
- Merge policy: keep **all** source attributions on a merged record; surface the
  **most recent** status but **show every source link** so a family can verify each.

### 1d. Result rendering (safety-first copy)
- Each merged result shows: name/age/location, **status with timestamp**, every
  contributing **source name**, an **"⚠️ unverified"** tag on citizen-registry data,
  and a **verify/update link** per source.
- Always append the ICRC authoritative handoff and the existing money/scam-free framing.
- Spanish first; translate to EN/both via the existing `llm.translate` cache.

### 1e. Wire into the bot
- `missing_persons` intent: if the user provides a name, run federated search and render
  results; otherwise return the existing KB + ICRC handoff (unchanged fallback).
- Add a tiny conversational capture ("reply with the name, and age/city if you have it")
  using the existing session state machine — no new framework.

**Done when.** `search("Maria Perez")` fan-outs across ≥2 adapters, dedupes overlapping
records, and renders results carrying source + "unverified" + verify link; one adapter
forced to throw still returns the others; unit tests cover the resolver; offline smoke
test passes with mocked adapters (no live calls in CI).

**Guardrails enforced here.** Live-not-scraped; source + unverified labels; ICRC handoff;
fail-soft isolation; no PII persisted (search is stateless — results are not written to
SQLite).

---

## Phase 2 — Cost optimizations in code (1 day)

Make it cheap enough to run at diaspora scale.

- **Haiku by default** for classify/translate (config flip + verify call sites).
- **Deterministic router ahead of the LLM:** numeric menu + a keyword table catch the
  common intents with zero tokens; the classifier is the fallback, not the front door.
  (Partly present today — formalize and expand the keyword table per language.)
- **Prompt caching** on the classifier system prompt and the translate system prompt
  (~90% off cached input).
- **Per-day token/cost meter:** lightweight counter (in SQLite) logging tokens in/out
  per call type, exposed at `GET /metrics` for a daily glance.

**Done when.** A menu tap or keyword hits zero model calls; classifier/translate run on
Haiku with caching on; `/metrics` shows today's call counts and an estimated $ figure.

---

## Phase 3 — Launch-critical content & deploy (parallelizable, 1–2 days)

These can run alongside Phases 1–2; they need Edgar's local knowledge and accounts.

- **Fill `resources.yaml`** — replace all 6 `VERIFICAR` placeholders with confirmed
  shelters / food points / clinics / mental-health lines. _Verified local data is what
  makes this a lifeline._ I can research candidate sources; Edgar confirms before merge.
- **Deploy `/con-venezuela/`** static site to Vercel; print the poster; confirm the QR
  opens the coupon.
- **Stand up the bot** on the Twilio WhatsApp sandbox: `.env` + tunnel + webhook at
  `/whatsapp`; live test; then register a real WhatsApp sender.
- **Entry point:** generate the `wa.me/<number>` link + QR; add to the café posters.

**Done when.** Posters point at a live coupon; a phone can message the sandbox number and
walk language → menu → a KB answer → a hero-network post end to end.

---

## Phase 4 — Needs heatmap & analytics (1–2 days, Edgar's analytics wheelhouse)

- Log **anonymized `intent + coarse location + timestamp`** (no PII) to BigQuery.
- Build a live "what's needed where" view to guide relief routing.

**Done when.** A dashboard shows intent volume by region over time, with no
personally identifying data in the pipeline.

---

## Phase 5 — Conversation & reliability polish (ongoing)

- Upgrade replies to WhatsApp **interactive list/buttons** (beyond the sandbox).
- Opt-in **aftershock alerts** (poll USGS; push via approved template messages).
- Move SQLite → Postgres when concurrency warrants.
- Notify-on-match for hero-network posts saved with consent but no match yet.

---

## Phase 6 — Network, compliance & funding (parallel ops track)

Mostly outreach and paperwork, tracked here so engineering and ops stay in sync.

- Outreach drafts (EN/ES) from Edgar's Gmail: GEM, Direct Relief, Orlando Health
  Foundation, registry creators (offer dedupe/merge help), diaspora groups, press.
- Route donations through a registered 501(c)(3) / fiscal sponsor — never collect cash
  personally; check GA charitable-solicitation registration.
- Apply for nonprofit/crisis credits (Anthropic, Twilio.org, cloud providers).

---

## Sequencing at a glance

| Phase | Track | Depends on | Owner |
|------|-------|-----------|-------|
| 0 Local run | eng | — | agent |
| 1 Registry search | eng | 0 | agent + Edgar (sources) |
| 2 Cost opt | eng | 0 | agent |
| 3 Content & deploy | ops/eng | accounts | Edgar + agent |
| 4 Heatmap | data | 0, BigQuery | Edgar |
| 5 Polish | eng | 3 | agent |
| 6 Network/compliance | ops | — | Edgar |

Phases 1 and 2 are the engineering critical path; 3 and 6 run in parallel as accounts
and local data become available.

---

## What I need from Edgar to keep moving

1. **Anthropic API key** in `.env` (Haiku) — for live classify/translate + Phase 1 testing.
2. **Confirmation of the registry query surfaces** — I'll propose what each adapter
   should hit; you sanity-check before we point at live services.
3. **Verified local data** for the 6 `VERIFICAR` slots (Phase 3) — I'll draft, you confirm.
4. **Twilio sandbox creds** when we're ready to put it on a real phone (Phase 3).
