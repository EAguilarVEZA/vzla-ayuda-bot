# Testing the bot — before any phone or WhatsApp number

You can test the **entire** bot without Twilio and without a phone. Two ways.

## What keys you need
| To test… | Need |
|---|---|
| The menu, hero network, search flow, safety, all logic | **nothing** |
| Free-text understanding ("estoy buscando a mi hermano") + translation | **Anthropic API key** (Haiku, cheap) |
| Real WhatsApp / SMS to real phones | Twilio (or Meta Cloud API) + your Business number |

Get the **Anthropic key first** — it's 5 minutes and unlocks the smart parts.
Twilio comes later, with the number.

## Option A — browser simulator (recommended)
A WhatsApp-style chat that talks to the real bot.

**Locally:**
```
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...     # optional but recommended
uvicorn app.main:app --reload --port 8000
```
Open **http://localhost:8000/sim** and chat. Tap the quick buttons or type
anything in Spanish or English. "New tester" simulates a fresh user.

**After you deploy** (Render blueprint — see GO_LIVE.md): open
`https://<your-app>.onrender.com/sim`. This is the fastest way to test on a real
server before you have the WhatsApp number.

## Option B — terminal
```
export ANTHROPIC_API_KEY=sk-ant-...     # optional
python scripts/chat.py
```
Type messages; `/reset` for a new tester, `/quit` to exit.

## What else to open while testing
- **Management dashboard:** `dashboard/index.html` (live once the server runs; reads `/metrics/daily`).
- **Org portal:** `org-portal/index.html` — paste the API base + a key from
  `python scripts/make_partner_key.py "Org Name"`, then push shelter capacity and
  watch it appear inside the bot's shelter answer.

## A good 2-minute test script
1. `hola` → pick a language → you get the menu.
2. `1` → type `María Pérez, 34, La Guaira` → federated search result with sources.
3. `8` → `necesito` → `traduccion` → `remota` → `Venezuela` → describe → contact →
   `si`. Open a second tester, register a US translation **offer**, and watch them match.
4. Try a scam post ("send money by Zelle first") → it's blocked.
5. `reportar`, `alertas`, `compartir`, `resuelto`, `borrar` → all the commands.
