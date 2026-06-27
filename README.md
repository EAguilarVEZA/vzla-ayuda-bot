# Ayuda Venezuela — WhatsApp/SMS Help Hub

A Spanish-first WhatsApp + SMS bot that helps people affected by the June 2026
Venezuela earthquakes: find shelter, food, supplies, medical care, local events,
search/report missing people, and connect with others offering help.

Same pattern as Jarvis: **Claude (brain) + FastAPI (webhook) + Twilio (channel)**.

## What it does
- **Bilingual (ES/EN/both) with two-way translation.** Each user picks a language;
  the interface is hand-translated and free-text (descriptions, matches) is translated
  by Claude — so an English volunteer in the US and a Spanish speaker in Venezuela can
  collaborate, each reading the other in their own language.
- Understands Spanish/English (Claude classifies intent).
- Answers **only** from a vetted knowledge base (`app/kb/resources.yaml`) — no invented info.
- Hands off missing-person search to the **authoritative ICRC** system, plus the
  citizen registries (clearly labeled unverified).
- **Hero network (the core):** anyone can register as *needing help* or *wanting to
  help (a hero/volunteer)*. People say what they need and see who's willing to help.
  - **Cross-border by design:** *remote* help (translation, info, coordination,
    fundraising) matches US ↔ Venezuela regardless of country; *in-person* help matches
    within the same region/location.
  - Consent + safety rails: contacts shared only on consent; money-scam warnings on
    every match; housing/money/minors redirect to vetted organizations.
  - `See network requests` lets people browse open offers and needs.
- Privacy: stores minimal data; `DELETE`/`BORRAR` wipes a user's data.

## Project layout
```
app/
  main.py        FastAPI + Twilio webhook (/whatsapp, /sms)
  bot.py         language onboarding, routing, the hero-network flow, browse
  i18n.py        bilingual interface strings (es/en/both)
  llm.py         Claude intent classifier + two-way translator
  knowledge.py   loads + renders the vetted KB
  matching.py    SQLite: users(language) + hero-network board + sessions
  safety.py      guardrail copy
  config.py      env config
  kb/resources.yaml   <-- EDIT THIS with verified local data
```

## Quick start (live in ~15 min)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in keys
uvicorn app.main:app --reload --port 8000
```
Expose it so Twilio can reach it (pick one):
```bash
npx localtunnel --port 8000        # or: cloudflared tunnel --url http://localhost:8000
```
In the **Twilio Console → Messaging → WhatsApp sandbox**, set the inbound webhook
to `https://<your-tunnel>/whatsapp`. Join the sandbox from your phone (send the
join code to the sandbox number), then text it.

## How people reach the bot
- **wa.me link:** `https://wa.me/<number>?text=hola` — drop in posts, the website, texts.
- **QR code:** point a QR at that wa.me link (reuse the poster generator) so the
  café flyers open the chat directly.

## Go live (beyond sandbox)
1. Register a WhatsApp sender (Twilio or Meta WhatsApp Cloud API) with a real number.
2. For **proactive** messages (e.g. aftershock alerts), use approved **template
   messages** — WhatsApp only allows free-form replies within 24h of a user message.
3. Move SQLite → Postgres if volume grows.

## Extend it (roadmap hooks)
- **Verified local data:** replace every `VERIFICAR` in `resources.yaml`.
- **Interactive buttons/lists:** upgrade replies from numbered text to WhatsApp
  list messages via Twilio Content API / Meta Cloud API.
- **Needs heatmap:** log each `intent + location` (anonymized) to BigQuery to map
  what's needed where, in real time — feeds relief routing.
- **Aftershock alerts:** poll USGS and push opt-in template messages.
- **Scam checker:** add an intent that takes a URL and returns verification steps.

## Guardrails (don't remove)
- Crowdsourced registries are labeled **unverified**; never assert someone is
  found/safe/dead.
- Always offer the ICRC authoritative handoff.
- Never auto-share contacts; consent required; money-scam warnings on every match.
- Route housing/money/minors to vetted orgs, not strangers.
- Keep Spanish crisis/mental-health resources reachable.
