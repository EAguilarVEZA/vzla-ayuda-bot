# Go-Live Runbook — Ayuda Venezuela Bot

How to take the bot from the Twilio sandbox to a real, shareable, one-tap service.
The single most important step is getting an **approved WhatsApp Business number**
(Step 2) — without it, every new person must first text a join code, which kills
sharing.

---

## Step 0 — What "live" means

Three things must be true for a stranger to use the bot with one tap:
1. The FastAPI server is **deployed** at a public HTTPS URL.
2. The bot has an **approved WhatsApp Business sender** (not the sandbox).
3. The **`wa.me` link + QR** point at that number and are on the posters / shared.

---

## Step 1 — Deploy the server

Any host that gives you a public HTTPS URL works (Render, Railway, Fly.io, a cloud
VM, etc.). Minimum:

```
pip install -r requirements.txt
# set env vars (see .env.example):
ANTHROPIC_API_KEY=...           # the bot's brain (Haiku by default)
BOT_MODEL=claude-haiku-4-5
DB_PATH=/data/ayuda.db          # a persistent disk
PUBLIC_BOT_LINK=https://wa.me/<your-number>?text=Hola
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Move SQLite → Postgres when concurrency grows. Keep `/metrics/daily` reachable for
the dashboard (CORS is already open for GET).

---

## Step 2 — Get an approved WhatsApp Business number (the unlock)

### The three WhatsApp "tiers" — you need the third
- **WhatsApp (personal app)** — not for bots.
- **WhatsApp Business app** — free small-business app; still manual, not the API.
- **WhatsApp Business Platform / Cloud API** — what powers an automated bot at
  scale. This is what we need.

### Can I convert my personal number? (Edgar's question)
**Technically yes, but don't.** A number can only live in **one** place at a time —
personal app, Business app, or the API. To register a number to the Business
Platform you must **first delete its existing WhatsApp account**, which means you'd
**lose your personal WhatsApp** on that number. The number can still make normal
calls/SMS, but it can no longer be used in the WhatsApp Messenger app.

**Recommendation: use a dedicated number, not your personal one.** Get a spare
number that is *not* active on any WhatsApp app — a new SIM, a VoIP/Twilio number,
or a Google Voice line — as long as it can receive the one-time verification code
by SMS or voice call. Keep your personal WhatsApp intact.

### What you'll need to register
- A **Meta business portfolio** + a **WhatsApp Business Account (WABA)**.
- **Business verification** with Meta: a legally registered entity and
  government-issued documentation (e.g. certificate of incorporation), plus a live
  **website with a privacy policy** page. → Register under the project's
  **501(c)(3) / fiscal sponsor**, not as an individual.
- A **payment card** on the WhatsApp Business Manager account for messaging billing.
- The dedicated phone number (above), verified via the register endpoint.

In **2026**, accounts that complete business verification can jump messaging tiers
much faster (straight toward the 100K/day tier with a good quality rating).

### Two paths (pick one)
- **Twilio / BSP (fastest to start).** Twilio is a WhatsApp Business Solution
  Provider; it walks you through sender registration, Meta business verification,
  and display-name approval. Our code's `WHATSAPP_PROVIDER=twilio` path targets this.
- **Meta Cloud API (direct).** Slightly more setup, lower per-message cost, and our
  `WHATSAPP_PROVIDER=cloud` path posts the native interactive list inline (just add
  `WHATSAPP_CLOUD_TOKEN` + `WHATSAPP_PHONE_ID`).

### The 24-hour window (why a reply bot is easy)
Inside **24 hours** of a user's last message you can send **free-form** replies (no
template needed) — exactly how this bot works. Templates are only required to
*initiate* a conversation outside that window (e.g. opt-in aftershock alerts).

### Nonprofit credits — ask for them
Apply for nonprofit/crisis credits: **Twilio.org**, **Meta/WhatsApp** nonprofit
programs, **Anthropic** credits, and cloud-provider nonprofit tiers. This can cover
most of the channel + AI cost.

---

## Step 3 — Flip it on

1. Point the WhatsApp sender's inbound webhook at `https://<your-host>/whatsapp`.
2. Set `WHATSAPP_INTERACTIVE=1` (+ provider creds) so the menu renders as the native
   list; it falls back to grouped text automatically.
3. Set `PUBLIC_BOT_LINK` to your number's `wa.me` link.
4. Generate the entry assets:
   ```
   python scripts/make_entry_qr.py +<your-number> --out dashboard/entry_qr.png
   ```
   Put the QR on `con-venezuela/poster.html` and the café posters; drop the link in
   diaspora WhatsApp groups.

---

## Step 4 — Launch checklist

- [ ] Server deployed, `/` health OK, `/metrics/daily` returns JSON.
- [ ] Dedicated WhatsApp Business number approved + verified (personal number untouched).
- [ ] Webhook verified; send "Hola" from a real phone → language → menu works.
- [ ] `resources.yaml` `VERIFICAR` placeholders filled with verified local data.
- [ ] `PUBLIC_BOT_LINK` set; QR printed; tested end-to-end (scan → bot opens).
- [ ] Guardrails reviewed (consent, high-risk redirect, money warnings, DELETE).
- [ ] Soft launch in one trusted group; watch the dashboard; then open the floodgates.

---

## Sources
- [WhatsApp Business sender registration prerequisites — Infobip](https://www.infobip.com/docs/whatsapp/get-started/sender-registration)
- [Business phone numbers — Meta for Developers](https://developers.facebook.com/documentation/business-messaging/whatsapp/business-phone-numbers/phone-numbers)
- [Overview of the WhatsApp Business Platform with Twilio](https://www.twilio.com/docs/whatsapp/api)
- [WhatsApp Business message limits 2026 — Uptail](https://www.uptail.ai/blog/how-many-messages-can-you-send-on-whatsapp-business-limits-explained-for-2026)
